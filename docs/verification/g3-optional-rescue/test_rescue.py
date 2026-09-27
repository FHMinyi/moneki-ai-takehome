"""Immutable c708 provider output and tool-fact replay, with networking forbidden."""
import copy
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'starter'), str(ROOT / 'eval')]
from kbqa.service import Service
from kbqa.config import load_settings
from kbqa.live import LiveEngine
from kbqa.trace import Trace
from kbqa.llm import LLMClient, LLMError

SOURCE = ROOT / 'docs/verification/g3-05/final-c7084d6/eval-live/chat-trace.jsonl'

def original(number):
    return next(r['response'] for r in map(json.loads, SOURCE.open())
                if r.get('path') == '/api/trace/t-20260901-%04d' % number)

@pytest.fixture(scope='module')
def service(tmp_path_factory):
    return Service(replace(load_settings(), var_dir=tmp_path_factory.mktemp('rescue'),
                          llm_base_url='', llm_api_key='', llm_model=''))

def replay(service, number, mutate=None):
    saved = original(number)
    records = copy.deepcopy(saved['llm_calls'])
    if mutate:
        mutate(records)
    calls = iter(records)
    tools = iter(s['detail'] for s in saved['steps'] if s['step'] == 'tool')
    plan = service.planner.plan(saved['question'])
    class Client:
        def chat_with_retry(self, messages, specs, **kwargs):
            record = next(calls)
            kwargs['on_call'](record)
            msg = record['response']['choices'][0]['message']
            return SimpleNamespace(content=msg.get('content'), tool_calls=msg.get('tool_calls', []), message=msg)
    def run(name, params, **kwargs):
        old = next(tools)
        assert (name, params) == (old['tool'], old['params'])
        actual = service.run_tool(name, params, **kwargs)
        if name == 'search_kb' and 'error' not in old['result']:
            signature = lambda e: {k:v for k,v in e.items() if k != 'evidence_id'}
            fresh = [signature(e) for e in actual['evidence']]
            for e in old['result']['evidence']:
                assert signature(e) in fresh
        else:
            assert actual == old['result']
        return old['result']
    trace = Trace('replay-%s' % number, saved['question'])
    engine = LiveEngine(Client(), service.answerer, run, service.settings.today.isoformat(), service.data_period)
    with patch.object(LLMClient, '_post', side_effect=AssertionError('provider network forbidden')):
        answer = engine.answer(plan, trace, [])
    return answer, trace

def test_c07(service):
    answer, _ = replay(service, 13)
    assert answer.answer_type == 'doc'
    assert {'KB-029'} == {c['doc_id'] for c in answer.citations}
    assert '35%' in answer.answer
    assert len([s for s in _.steps if s['step'] == 'document_binding']) == 1

def test_h06(service):
    answer, trace = replay(service, 24)
    assert answer.answer_type == 'data'
    assert answer.data_evidence[0]['result']['period_b']['net_revenue'] == 0
    assert '原因' in answer.answer and ('无法确定' in answer.answer or '未找到' in answer.answer)
    assert len([s for s in trace.steps if s['step'] == 'tool' and 'error' in s['detail']['result']]) == 4

@pytest.mark.parametrize('number,key', [(13,'facts'), (24,'results')])
def test_forged_reference(service, number, key):
    def mutate(records):
        message = records[-1]['response']['choices'][0]['message']
        payload = json.loads(message['content'])
        payload[key][0]['evidence_id' if key == 'facts' else 'call_id'] = 'invented'
        message['content'] = json.dumps(payload)
    with pytest.raises(LLMError):
        replay(service, number, mutate)

def test_original_h06_trace_size():
    from kbqa import trace as module
    saved = original(24)
    compact = module.compact_trace(saved) if hasattr(module, 'compact_trace') else saved
    assert len(json.dumps(compact, ensure_ascii=False, separators=(',', ':')).encode()) <= 2 * 1024 * 1024
    assert module.expand_trace(compact) == saved

@pytest.mark.parametrize('error,success,expected', [
    ('参数 top_k 必须是 1 至 10 的整数', True, 'refusal'),
    ('参数 top_k 必须是 1 至 10 的整数', False, 'error'),
    ('工具 search_kb 执行失败：source unavailable', True, 'error'),
    ('unclassified failure', True, 'error'),
])
def test_failure_recovery_boundary(service, error, success, expected):
    messages = [{'role':'assistant', 'tool_calls':[{'id':'bad','function':{'name':'search_kb','arguments':json.dumps({'query':'old','top_k':20})}}]}]
    if success:
        messages.append({'role':'assistant', 'tool_calls':[{'id':'good','function':{'name':'search_kb','arguments':json.dumps({'query':'refined','top_k':10})}}]})
    messages.append({'role':'assistant','content':json.dumps({'answer_type':'refusal','reason':'insufficient_evidence'})})
    replies = iter(messages)
    class Client:
        def chat_with_retry(self, *args, **kwargs):
            m=next(replies)
            return SimpleNamespace(message=m, tool_calls=m.get('tool_calls',[]), content=m.get('content'))
    def run(name, params, **kwargs):
        return {'error':error} if params['top_k']==20 else {'evidence':[], 'rejected':[], 'diagnostics':{}, 'scope':{}}
    engine=LiveEngine(Client(),service.answerer,run,'2026-09-01',service.data_period)
    trace=Trace('failure-boundary','why')
    if expected=='error':
        with pytest.raises(LLMError, match='tool_failure'):
            engine.answer(service.planner.plan('为什么'),trace,[])
    else:
        answer=engine.answer(service.planner.plan('为什么'),trace,[])
        assert answer.answer_type=='refusal'
        assert any(s['step']=='tool_failure_recovered' for s in trace.steps)
    assert any(s['step']=='tool' and s['detail']['result']=={'error':error} for s in trace.steps)


def test_trace_unequal_fields_and_small_shape():
    from kbqa.trace import compact_trace, expand_trace
    small=original(13)
    assert compact_trace(small)==small
    saved=original(24)
    saved['llm_calls'][0]['prompt']+=' preserved whitespace '
    pos=next(i for i,s in enumerate(saved['steps']) if s['step']=='tool' and s['detail']['tool']=='search_kb')
    saved['steps'][pos]['detail']['result']['diagnostics']['extra']='not identical'
    result=compact_trace(saved)
    assert result['llm_calls'][0]['prompt']==saved['llm_calls'][0]['prompt']
    assert result['steps'][pos]['detail']['result']['diagnostics']==saved['steps'][pos]['detail']['result']['diagnostics']
    assert expand_trace(result)==saved


def test_real_http_official_reader(service, monkeypatch, tmp_path):
    import socket, threading, time
    import uvicorn
    from kbqa import server
    from kbqa.trace import expand_trace
    from run_eval import Client
    saved=original(24)
    service.traces._data[saved['trace_id']]=saved
    monkeypatch.setattr(server,'_service',service)
    sock=socket.socket()
    sock.bind(('127.0.0.1',0))
    port=sock.getsockname()[1]
    app=uvicorn.Server(uvicorn.Config(server.app,log_level='error'))
    thread=threading.Thread(target=app.run,kwargs={'sockets':[sock]},daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if app.started:break
            time.sleep(.01)
        response=Client('http://127.0.0.1:%d'%port).get('/api/trace/'+saved['trace_id'])
        assert response.ok, response
        assert expand_trace(response.data)==saved
        import os
        output=os.environ.get('RESCUE_OUT')
        if output:
            summary={'original_bytes':len(json.dumps(saved,ensure_ascii=False,separators=(',',':')).encode()),
                     'http_bytes':len(response.body.encode()),'roundtrip_equal':True,
                     'reference_count':len(response.data['_trace_references']['references']),
                     'official_reader_ok':True,'port':port,'closed_after_test':True}
            Path(output).mkdir(parents=True,exist_ok=True)
            (Path(output)/'trace-http.json').write_text(json.dumps(summary,indent=2)+'\n')
    finally:
        app.should_exit=True
        thread.join(timeout=5)
        sock.close()
        assert not thread.is_alive()
