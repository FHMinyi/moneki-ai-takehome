"""Early planner exits must not bypass explicit trend-condition validation."""
import json
import sys
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'starter'))
from kbqa import server
from kbqa.config import load_settings
from kbqa.llm import LLMClient, LLMReply
from kbqa.service import Service

REFERENCE = {'type': 'daily_trend', 'start': '2026-06-01', 'end': '2026-06-30',
             'store_id': 'S02', 'metric': 'net_revenue'}


@pytest.fixture()
def live_api(tmp_path, monkeypatch):
    settings = replace(load_settings(), var_dir=tmp_path / 'var', llm_base_url='http://controlled.invalid',
                       llm_api_key='synthetic-dummy', llm_model='controlled')
    service = Service(settings)
    monkeypatch.setattr(server, '_service', service)
    return TestClient(server.app), service


def ask(client, question):
    response = client.post('/api/chat', json={'session_id': 'early-plan', 'question': question,
                                              'context': REFERENCE})
    assert response.status_code == 200
    body = response.json()
    trace = client.get('/api/trace/' + body['trace_id']).json()
    return body, trace


def controlled(monkeypatch, tool, params):
    call = {'id': 'scope-call', 'type': 'function',
            'function': {'name': tool, 'arguments': json.dumps(params)}}
    final = json.dumps({'answer_type': 'data', 'results': [{'call_id': 'scope-call',
                                                          'metric': 'net_revenue'}]})
    replies = iter([LLMReply({'role': 'assistant', 'content': '', 'tool_calls': [call]},
                             'tool_calls', '', [call], 0),
                    LLMReply({'role': 'assistant', 'content': final}, 'stop', final, [], 0)])
    model_calls = []
    def respond(self, messages, tools, budget, on_call):
        model_calls.append(messages)
        return next(replies)
    monkeypatch.setattr(LLMClient, 'chat_with_retry', respond)
    return model_calls


@pytest.mark.parametrize('question,rejection', [
    ('预测模型训练前，请查询S99六月净营业额。', 'unknown_store'),
    ('预测模型训练前，请查询S02 P99六月净营业额。', 'unknown_product'),
    ('预测模型训练前，请查询S02现在净营业额。', 'out_of_period'),
])
def test_early_exit_invalid_explicit_condition_never_falls_back(live_api, monkeypatch, question, rejection):
    client, service = live_api
    assert service.planner.plan(question).kind == 'out_of_scope'
    calls = []
    monkeypatch.setattr(LLMClient, 'chat_with_retry', lambda *args, **kwargs: calls.append(True))
    body, trace = ask(client, question)
    assert body['answer_type'] == 'refusal' and body['data_evidence'] == []
    assert calls == [] and trace['errors'] == []
    resolution = next(s['detail'] for s in trace['steps'] if s['step'] == 'context_resolution')
    assert resolution['rejection'] == rejection and resolution['effective'] is None


def test_early_exit_explicit_whole_period_uses_data_period(live_api, monkeypatch):
    client, service = live_api
    question = '预测模型训练前，请查询S02全部时间净营业额。'
    assert service.planner.plan(question).kind == 'out_of_scope'
    params = {'start': service.data_period['start'], 'end': service.data_period['end'],
              'store_id': 'S02'}
    calls = controlled(monkeypatch, 'query_metrics', params)
    body, trace = ask(client, question)
    assert body['answer_type'] == 'data' and len(calls) == 2
    assert body['data_evidence'][0]['result'] == service.tools.query_metrics(**params)
    resolution = next(s['detail'] for s in trace['steps'] if s['step'] == 'context_resolution')
    assert resolution['effective']['start'] == service.data_period['start']
    assert resolution['effective']['end'] == service.data_period['end']
    assert resolution['source']['window'] == 'question'
    assert trace['errors'] == []


def test_early_exit_two_windows_compare_uses_both_windows(live_api, monkeypatch):
    client, service = live_api
    question = '预测模型训练前，请比较S02六月和七月净营业额。'
    assert service.planner.plan(question).kind == 'out_of_scope'
    params = {'start_a': '2026-06-01', 'end_a': '2026-06-30',
              'start_b': '2026-07-01', 'end_b': '2026-07-31', 'store_id': 'S02'}
    calls = controlled(monkeypatch, 'compare_periods', params)
    body, trace = ask(client, question)
    assert body['answer_type'] == 'data' and len(calls) == 2
    assert body['data_evidence'][0]['result'] == service.tools.compare_periods(**params)
    assert '6 月' in body['answer'] and '7 月' in body['answer']
    resolution = next(s['detail'] for s in trace['steps'] if s['step'] == 'context_resolution')
    assert resolution['effective']['compare_window'] == ['2026-07-01', '2026-07-31']
    assert resolution['source']['compare_window'] == 'question'
    assert trace['errors'] == []


def test_two_windows_without_comparison_clarifies_instead_of_picking_first(live_api, monkeypatch):
    client, _ = live_api
    calls = []
    monkeypatch.setattr(LLMClient, 'chat_with_retry', lambda *args, **kwargs: calls.append(True))
    body, trace = ask(client, '预测模型训练前，请查询S02六月和七月净营业额。')
    assert body['answer_type'] == 'clarify' and body['data_evidence'] == []
    assert calls == [] and trace['errors'] == []
    resolution = next(s['detail'] for s in trace['steps'] if s['step'] == 'context_resolution')
    assert resolution['clarification'] == 'multiple_periods_without_comparison'
