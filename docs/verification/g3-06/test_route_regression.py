"""Regression for G3-01 live semantic routing with and without trend context."""
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'starter'))
from kbqa.config import load_settings
from kbqa.llm import LLMReply, LLMClient
from kbqa.service import Service
from kbqa.schemas import Answer

QUESTION = '预测模型训练前，请查询S02六月牛肉poke净营业额。'
CONTEXT = {'type': 'daily_trend', 'start': '2026-06-01', 'end': '2026-06-30',
           'store_id': 'S02', 'metric': 'net_revenue'}


@pytest.mark.parametrize('context', [None, CONTEXT])
def test_clear_data_request_reaches_live_tools_despite_overbroad_preamble(tmp_path, monkeypatch, context):
    settings = replace(load_settings(), var_dir=tmp_path / 'var', llm_base_url='http://controlled.invalid',
                       llm_api_key='synthetic-dummy', llm_model='controlled')
    service = Service(settings)
    assert service.planner.plan(QUESTION).kind == 'out_of_scope'
    params = {'start': '2026-06-01', 'end': '2026-06-30', 'store_id': 'S02', 'product_id': 'P06'}
    call = {'id': 'route-call', 'type': 'function',
            'function': {'name': 'query_metrics', 'arguments': json.dumps(params)}}
    replies = iter([
        LLMReply({'role': 'assistant', 'content': '', 'tool_calls': [call]}, 'tool_calls', '', [call], 0),
        LLMReply({'role': 'assistant', 'content': json.dumps({'answer_type': 'data', 'results': [
            {'call_id': 'route-call', 'metric': 'net_revenue'}]})}, 'stop', json.dumps({'answer_type': 'data',
            'results': [{'call_id': 'route-call', 'metric': 'net_revenue'}]}), [], 0),
    ])
    model_calls = []
    def controlled(self, messages, tools, budget, on_call):
        model_calls.append(messages)
        return next(replies)
    monkeypatch.setattr(LLMClient, 'chat_with_retry', controlled)
    result = service.chat('route-regression', QUESTION, context)
    assert result['answer_type'] == 'data'
    assert len(model_calls) == 2
    assert result['data_evidence'][0]['result'] == service.tools.query_metrics(**params)
    trace = service.get_trace(result['trace_id'])
    if context:
        resolution = next(step['detail'] for step in trace['steps'] if step['step'] == 'context_resolution')
        assert resolution['effective']['start'] == '2026-06-01'
        assert resolution['effective']['store_id'] == 'S02'
    else:
        assert not any(step['step'] == 'context_resolution' for step in trace['steps'])


def test_context_path_preserves_final_credential_redaction(tmp_path, monkeypatch):
    synthetic_key = 'synthetic-g306-secret-for-test-only'
    settings = replace(load_settings(), var_dir=tmp_path / 'var', llm_base_url='http://controlled.invalid',
                       llm_api_key=synthetic_key, llm_model='controlled')
    service = Service(settings)
    def diagnostic_writer(plan, trace, history, effective):
        assert effective == {'start': '2026-06-01', 'end': '2026-06-30',
                             'store_id': 'S02', 'metric': 'net_revenue'}
        trace.steps.append({'step': 'untrusted', 'detail': synthetic_key})
        trace.errors.append({'message': synthetic_key})
        trace.llm_calls.append({'request': synthetic_key})
        return Answer('拒答 ' + synthetic_key, 'refusal', notes=['note ' + synthetic_key])
    monkeypatch.setattr(service, '_run_engine', diagnostic_writer)
    answer = service.chat('context-credential-check', '这段时间净营业额是多少？', CONTEXT)
    trace = service.get_trace(answer['trace_id'])
    assert synthetic_key not in json.dumps({'answer': answer, 'trace': trace}, ensure_ascii=False)
    assert synthetic_key not in json.dumps(service.sessions.history('context-credential-check'), ensure_ascii=False)
    assert '[REDACTED]' in answer['answer']


@pytest.mark.parametrize('question,kind', [
    ('S99 六月净营业额是多少？', 'unknown_entity'),
    ('2027年1月 S02 净营业额是多少？', 'out_of_period'),
])
def test_reference_does_not_overrule_unknown_store_or_out_of_period(tmp_path, monkeypatch, question, kind):
    settings = replace(load_settings(), var_dir=tmp_path / 'var', llm_base_url='http://controlled.invalid',
                       llm_api_key='synthetic-dummy', llm_model='controlled')
    service = Service(settings)
    assert service.planner.plan(question).kind == kind
    calls = []
    monkeypatch.setattr(LLMClient, 'chat_with_retry', lambda *args, **kwargs: calls.append(True))
    answer = service.chat('hard-stop', question, CONTEXT)
    assert answer['answer_type'] == 'refusal'
    assert answer['data_evidence'] == []
    assert calls == []
