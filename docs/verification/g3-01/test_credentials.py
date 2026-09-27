"""Full chat/trace boundary regression; synthetic credentials only, no paid calls."""
import json
import logging
import sys
import threading
import traceback
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'starter'))
from kbqa.config import load_settings
from kbqa.service import Service
from kbqa.llm import LLMClient, LLMError
from kbqa import server

SYNTHETIC_KEY = 'synthetic-G301-credential-for-regression-only'


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    service = Service(replace(load_settings(), var_dir=tmp_path/'var',
        llm_base_url='http://unused', llm_api_key=SYNTHETIC_KEY, llm_model='controlled'))
    monkeypatch.setattr(server, 'service', lambda: service)
    with TestClient(server.app) as client:
        yield client, service


def chat_and_trace(client):
    result = client.post('/api/chat', json={'session_id':'credential-check', 'question':'S02六月牛肉poke销量是多少？'})
    assert result.status_code == 200
    answer = result.json()
    trace_result = client.get('/api/trace/'+answer['trace_id'])
    assert trace_result.status_code == 200
    return answer, trace_result.json()


def test_non_json_echo_is_redacted_across_complete_http_chat(app_client, caplog):
    client, service = app_client
    class Echo(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            # Actual local HTTP response echoes the bearer credential.
            body=('upstream invalid JSON; credential='+self.headers['Authorization']).encode()
            self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    upstream=ThreadingHTTPServer(('127.0.0.1',0),Echo)
    threading.Thread(target=upstream.serve_forever,daemon=True).start()
    service.settings=replace(service.settings,llm_base_url=f'http://127.0.0.1:{upstream.server_port}')
    try:
        with caplog.at_level(logging.DEBUG):
            answer,trace=chat_and_trace(client)
        assert answer['answer_type']=='refusal'
        assert trace['llm_calls'][0]['status']==200
        assert trace['llm_calls'][0]['error']=='bad_json'
        assert 'invalid JSON' in trace['llm_calls'][0]['raw_response']
        assert SYNTHETIC_KEY not in json.dumps({'answer':answer,'trace':trace},ensure_ascii=False)
        assert SYNTHETIC_KEY not in caplog.text
        assert '[REDACTED]' in json.dumps(trace)
    finally: upstream.shutdown();upstream.server_close()


@pytest.mark.parametrize('kind', ['timeout','transport','unexpected','finish','http'])
def test_other_error_channels_and_exception_chains(app_client,monkeypatch,caplog,kind):
    client,_=app_client
    def post(*args):
        if kind=='finish':
            return httpx.Response(200,json={'choices':[{'finish_reason':SYNTHETIC_KEY,'message':{'role':'assistant','content':'untrusted'}}]})
        if kind=='http': return httpx.Response(401,text='error: '+SYNTHETIC_KEY)
        error={'timeout':httpx.ReadTimeout,'transport':httpx.ConnectError,'unexpected':RuntimeError}[kind]
        try: raise ValueError('cause '+SYNTHETIC_KEY)
        except ValueError as cause: raise error('failure '+SYNTHETIC_KEY) from cause
    monkeypatch.setattr(LLMClient,'_post',post)
    with caplog.at_level(logging.DEBUG): answer,trace=chat_and_trace(client)
    assert answer['answer_type']=='refusal'
    assert trace['errors']
    assert SYNTHETIC_KEY not in json.dumps({'answer':answer,'trace':trace},ensure_ascii=False)+caplog.text
    with pytest.raises(LLMError) as captured:
        LLMClient('http://unused',SYNTHETIC_KEY,'controlled').chat([])
    assert SYNTHETIC_KEY not in ''.join(traceback.format_exception(captured.value))
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_service_fallback_sanitizes_complete_exception_log(app_client,monkeypatch,caplog):
    client,service=app_client
    def broken(*args):
        try: raise ValueError('underlying '+SYNTHETIC_KEY)
        except ValueError as cause: raise RuntimeError('outer '+SYNTHETIC_KEY) from cause
    monkeypatch.setattr(service,'_run_engine',broken)
    with caplog.at_level(logging.ERROR): answer,trace=chat_and_trace(client)
    assert answer['answer_type']=='refusal'
    assert 'RuntimeError' in trace['errors'][0]['traceback']
    assert 'ValueError' in trace['errors'][0]['traceback']
    assert 'chat failed' in caplog.text
    assert SYNTHETIC_KEY not in json.dumps(trace)+caplog.text


def test_final_trace_boundary_and_normal_full_diagnostics(app_client,monkeypatch):
    client,service=app_client
    long_reasoning='normal diagnostic ' * 500
    content=json.dumps({'answer_type':'clarify','answer':'请补充日期。'},ensure_ascii=False)
    payload={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':content,'reasoning_content':long_reasoning}}], 'usage':{'prompt_tokens':12,'completion_tokens':7}}
    monkeypatch.setattr(LLMClient,'_post',lambda *args:httpx.Response(200,json=payload))
    answer,trace=chat_and_trace(client)
    assert answer['answer_type']=='clarify'
    assert trace['llm_calls'][0]['response']==payload
    assert trace['llm_calls'][0]['raw_reasoning']==long_reasoning
    assert trace['llm_calls'][0]['request']['tools']
    assert trace['llm_calls'][0]['request']['messages'][-1]['content']=='S02六月牛肉poke销量是多少？'


def test_final_output_boundary_covers_direct_diagnostic_writers(app_client,monkeypatch):
    from kbqa.schemas import Answer
    client,service=app_client
    def diagnostic_writer(plan,trace,history):
        # Independently exercise final serialization, even if a producer bypasses
        # step()/llm()/error() and forgets its own local redaction.
        trace.steps.append({'step':'untrusted','detail':SYNTHETIC_KEY})
        trace.errors.append({'message':SYNTHETIC_KEY,'traceback':'cause '+SYNTHETIC_KEY})
        trace.llm_calls.append({'request':{'untrusted':SYNTHETIC_KEY}})
        return Answer('拒答 '+SYNTHETIC_KEY,'refusal',notes=['note '+SYNTHETIC_KEY])
    monkeypatch.setattr(service,'_run_engine',diagnostic_writer)
    answer,trace=chat_and_trace(client)
    assert SYNTHETIC_KEY not in json.dumps({'answer':answer,'trace':trace})
    assert SYNTHETIC_KEY not in json.dumps(service.sessions.history('credential-check'))
    assert '[REDACTED]' in answer['answer']


def test_redaction_precedes_preview_truncation(app_client,monkeypatch):
    client,_=app_client
    monkeypatch.setattr(LLMClient,'_post',lambda *args:httpx.Response(200,text='x'*190+SYNTHETIC_KEY+' invalid JSON'))
    answer,trace=chat_and_trace(client)
    # A 200-character preview must not retain even the first ten key characters.
    assert SYNTHETIC_KEY[:10] not in json.dumps(trace)
    assert answer['answer_type']=='refusal'
