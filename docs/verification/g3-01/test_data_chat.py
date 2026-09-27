"""G3-01 regressions: real database tools, controlled model responses only."""
import json
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'starter'))
from kbqa.config import load_settings
from kbqa.service import Service
from kbqa.sessions import SessionStore
from kbqa.toolspec import TOOLS
from kbqa.llm import LLMClient, LLMReply
from kbqa.live import LiveEngine
from kbqa.trace import Trace


@pytest.fixture(scope='module')
def service(tmp_path_factory):
    return Service(replace(load_settings(), var_dir=tmp_path_factory.mktemp('g3'),
                           llm_base_url='', llm_api_key='', llm_model=''))


def test_sessions_are_isolated_and_snapshots_are_detached():
    sessions = SessionStore(max_sessions=2, max_turns=2)
    sessions.append('a', {'question': 'A', 'slots': {'x': 1}})
    assert sessions.history('b') == []
    snapshot = sessions.history('a')
    snapshot[0]['slots']['x'] = 9
    assert sessions.history('a')[0]['slots']['x'] == 1
    sessions.append(None, {'question': 'anonymous'})
    assert sessions.history(None) == []
    sessions.append('b', {'question': 'B'})
    sessions.append('c', {'question': 'C'})
    assert sessions.history('a') == []


def test_free_sql_is_not_declared_or_executable(service):
    assert 'run_sql' not in [t['function']['name'] for t in TOOLS]
    assert 'error' in service.run_tool('run_sql', {'sql': 'SELECT * FROM stores'})


@pytest.mark.parametrize('params', [
    {'start':'2026-06-01','end':'2026-06-30','sql':'DELETE FROM sales'},
    {'start':'2026-02-30','end':'2026-06-30'},
    {'start':'2026-06-30','end':'2026-06-01'},
    {'start':'2026-06-01','end':'2026-06-30','store_id':'S99'},
    {'start':['2026-06-01'],'end':'2026-06-30'},
])
def test_illegal_parameters_fail_before_query(service, params, monkeypatch):
    spy = Mock(side_effect=AssertionError('must not execute'))
    monkeypatch.setattr(service.tools, 'query_metrics', spy)
    assert 'error' in service.run_tool('query_metrics', params)
    spy.assert_not_called()


def run_live(service, content):
    params = {'start':'2026-06-01','end':'2026-06-30','store_id':'S02','product_id':'P06'}
    call = {'id':'metrics-1','type':'function','function':{'name':'query_metrics','arguments':json.dumps(params)}}
    replies = [LLMReply({'role':'assistant','content':'','tool_calls':[call], 'reasoning_content':'private thought'}, 'tool_calls','',[call],0),
               LLMReply({'role':'assistant','content':content},'stop',content,[],0)]
    client = Mock()
    client.chat_with_retry.side_effect = replies
    engine = LiveEngine(client, service.answerer, service.run_tool,'2026-09-01',service.data_period)
    trace = Trace('test', 'S02 六月牛肉poke销量是多少？')
    answer = engine.answer(service.planner.plan(trace.question), trace, [])
    return answer, trace, service.tools.query_metrics(**params)


def test_data_answer_binds_metric_to_real_tool_call(service):
    content = json.dumps({'answer_type':'data','results':[{'call_id':'metrics-1','metric':'qty'}]})
    answer, trace, actual = run_live(service, content)
    assert answer.answer_type == 'data'
    assert f"销量 {actual['qty']} 件" in answer.answer
    assert answer.data_evidence[0]['result'] == actual
    step = next(s for s in trace.steps if s['step'] == 'tool')
    assert step['detail']['result'] == actual


def test_arbitrary_prose_cannot_swap_metric_values(service):
    actual = service.tools.query_metrics('2026-06-01','2026-06-30','S02','P06')
    # This number really occurs in a result, but belongs to orders, not revenue.
    from kbqa.llm import LLMError
    with pytest.raises(LLMError):
        run_live(service, f"净营业额为 {actual['orders']} 元。")


def test_trace_keeps_complete_requests_responses_and_redacts_key(monkeypatch):
    text = '完整内容' * 1500
    payload = {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':text}}]}
    monkeypatch.setattr(LLMClient, '_post', lambda *a, **kw: httpx.Response(200,json=payload))
    records=[]
    LLMClient('http://local/prefix','secret-test-key','model').chat(
        [{'role':'user','content':text}], TOOLS, on_call=records.append)
    assert records[0]['request']['messages'][0]['content'] == text
    assert records[0]['request']['tools'] == TOOLS
    assert records[0]['response']['choices'][0]['message']['content'] == text
    assert 'secret-test-key' not in json.dumps(records)


@pytest.mark.parametrize('content', [
    {'answer_type':'data','results':[{'call_id':'forged','metric':'qty'}]},
    {'answer_type':'data','results':[{'call_id':'metrics-1','metric':'qty','value':6}]},
    {'answer_type':'data','results':[{'call_id':'metrics-1','metric':'store_id'}]},
])
def test_data_selection_rejects_forged_fields(service, content):
    from kbqa.llm import LLMError
    with pytest.raises(LLMError): run_live(service,json.dumps(content))


def test_tool_result_exposes_actual_call_reference(service):
    params={'start':'2026-06-01','end':'2026-06-30','store_id':'S02','product_id':'P06'}
    call={'id':'provider-generated-id','type':'function','function':{'name':'query_metrics','arguments':json.dumps(params)}}
    client=Mock()
    turns=[]
    def reply(messages,*args,**kwargs):
        if not turns:
            turns.append(True)
            return LLMReply({'role':'assistant','content':'','tool_calls':[call]},'tool_calls','',[call],0)
        content=json.loads(messages[-1]['content'])
        assert content['call_id']=='provider-generated-id'
        assert content['result']==service.tools.query_metrics(**params)
        final=json.dumps({'answer_type':'data','results':[{'call_id':content['call_id'],'metric':'qty'}]})
        return LLMReply({'role':'assistant','content':final},'stop',final,[],0)
    client.chat_with_retry.side_effect=reply
    trace=Trace('ref','S02六月牛肉poke销量')
    answer=LiveEngine(client,service.answerer,service.run_tool,'2026-09-01',service.data_period).answer(service.planner.plan(trace.question),trace,[])
    assert answer.answer_type=='data'


def test_model_error_echo_cannot_retain_credential(monkeypatch):
    from kbqa.llm import LLMError
    monkeypatch.setattr(LLMClient, '_post', lambda *a: httpx.Response(401,json={'error':{'message':'invalid secret-test-key'}}))
    records=[]
    with pytest.raises(LLMError) as exc:
        LLMClient('http://local','secret-test-key','model').chat([{'role':'user','content':'hello'}],on_call=records.append)
    assert 'secret-test-key' not in str(exc.value) + json.dumps(records)


def test_retry_uses_actual_elapsed_budget(monkeypatch):
    import time
    from kbqa.llm import LLMError
    client=LLMClient('http://local','key','model',timeout=120)
    calls=[]
    def chat(*args, **kwargs):
        calls.append(kwargs['timeout'])
        if len(calls)==1: raise LLMError('http_error','temporary',503)
        return 'ok'
    monkeypatch.setattr(client,'chat',chat)
    assert client.chat_with_retry([],budget=3)=='ok'
    assert len(calls)==2 and 2 < calls[1] < 3


def test_keepalive_and_total_deadline_use_real_http():
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from kbqa.llm import LLMError
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
            try:
                for _ in range(8): self.wfile.write(b'\n'); self.wfile.flush(); time.sleep(.04)
                self.wfile.write(json.dumps({'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'有效回答'}}]}).encode())
            except (BrokenPipeError,ConnectionResetError): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        client=LLMClient(f'http://127.0.0.1:{server.server_port}','dummy','model')
        assert client.chat([],timeout=2).content=='有效回答'
        records=[]; started=time.perf_counter()
        with pytest.raises(LLMError,match='timeout'):
            client.chat([],timeout=.12,on_call=records.append)
        assert time.perf_counter()-started < .5
        assert records[0]['error']=='timeout'
    finally: server.shutdown();server.server_close()
