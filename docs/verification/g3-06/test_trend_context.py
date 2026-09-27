"""G3-06: the referenced scope is validated, resolved and queried anew."""

import shutil
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'starter'))
from kbqa import server
from kbqa.config import load_settings
from kbqa.service import Service

REFERENCE = {'type': 'daily_trend', 'start': '2026-06-01', 'end': '2026-06-30',
             'store_id': 'S02', 'metric': 'net_revenue'}


@pytest.fixture()
def api(tmp_path, monkeypatch):
    settings = replace(load_settings(), var_dir=tmp_path / 'var',
                       llm_base_url='', llm_api_key='', llm_model='')
    service = Service(settings)
    monkeypatch.setattr(server, '_service', service)
    return TestClient(server.app), service


def ask(client, question, context=REFERENCE):
    return client.post('/api/chat', json={'session_id': 'trend-test', 'question': question,
                                          'context': context})


def step(trace, name):
    return next(item['detail'] for item in trace['steps'] if item['step'] == name)


def test_reference_scope_evidence_trace_and_replay(api):
    client, service = api
    response = ask(client, '这段时间净营业额是多少？')
    assert response.status_code == 200
    body = response.json()
    assert body['answer_type'] == 'data'
    actual = service.tools.query_metrics('2026-06-01', '2026-06-30', 'S02')
    assert body['data_evidence'][0]['result'] == actual
    assert body['data_evidence'][0]['params']['start'] == REFERENCE['start']
    assert body['data_evidence'][0]['params']['store_id'] == 'S02'
    assert str(actual['net_revenue']) in body['answer']
    trace = client.get('/api/trace/' + body['trace_id']).json()
    assert step(trace, 'request')['question'] == '这段时间净营业额是多少？'
    assert step(trace, 'request')['context'] == REFERENCE
    assert step(trace, 'context_validation')['valid'] is True
    assert step(trace, 'context_resolution')['effective']['start'] == '2026-06-01'
    assert step(trace, 'context_resolution')['source']['window'] == 'reference'
    assert step(trace, 'tool')['result'] == actual
    replay = ask(client, step(trace, 'request')['question'], step(trace, 'request')['context']).json()
    assert replay['data_evidence'] == body['data_evidence']


def test_question_override_ambiguity_and_legacy(api):
    client, service = api
    override = ask(client, '7月 S01 的净营业额是多少？').json()
    assert override['answer_type'] == 'data'
    assert override['data_evidence'][0]['result'] == service.tools.query_metrics('2026-07-01', '2026-07-31', 'S01')
    resolved = step(client.get('/api/trace/' + override['trace_id']).json(), 'context_resolution')
    assert resolved['source'] == {'window': 'question', 'store_id': 'question', 'metric': 'question'}
    clarify = ask(client, '这一周净营业额是多少？').json()
    assert clarify['answer_type'] == 'clarify' and clarify['data_evidence'] == []
    assert step(client.get('/api/trace/' + clarify['trace_id']).json(), 'context_resolution')['clarification']
    legacy = client.post('/api/chat', json={'session_id': 'legacy', 'question': 'S02 六月净营业额是多少？'})
    assert legacy.status_code == 200 and legacy.json()['answer_type'] == 'data'
    assert 'context' not in step(client.get('/api/trace/' + legacy.json()['trace_id']).json(), 'request') or step(client.get('/api/trace/' + legacy.json()['trace_id']).json(), 'request')['context'] is None


def test_live_tool_scope_gate_uses_resolved_conditions(api, monkeypatch):
    _, service = api
    plan = service.planner.plan('这段时间净营业额是多少？')
    from kbqa.trend_context import resolve
    effective = resolve(plan, plan.question, REFERENCE, service.catalog, service.settings.today,
                        service.data_period)['effective']
    def must_not_query(*args, **kwargs):
        raise AssertionError('wrong scope reached database')
    monkeypatch.setattr(service.tools, 'query_metrics', must_not_query)
    assert 'error' in service._run_scoped_tool('query_metrics', {'start': '2026-05-01', 'end': '2026-08-31', 'store_id': 'S02'}, effective, plan)
    assert 'error' in service._run_scoped_tool('query_metrics', {'start': '2026-06-01', 'end': '2026-06-30', 'store_id': 'S01'}, effective, plan)
    assert 'error' in service._run_scoped_tool('query_metrics', {'start': '2026-06-01', 'end': '2026-06-30', 'store_id': 'S02', 'product_id': 'P06'}, effective, plan)
    assert 'error' in service._run_scoped_tool('by_store', {'start': '2026-06-01', 'end': '2026-06-30'}, effective, plan)
    assert 'error' in service._run_scoped_tool('compare_periods', {'start_a': '2026-06-01', 'end_a': '2026-06-30', 'start_b': '2026-07-01', 'end_b': '2026-07-31'}, effective, plan)


@pytest.mark.parametrize('bad', [
    {**REFERENCE, 'sql': 'SELECT * FROM sales'},
    {**REFERENCE, 'tool': 'query_metrics'},
    {**REFERENCE, 'amount': 999999},
    {**REFERENCE, 'start': '2026-02-30'},
    {**REFERENCE, 'store_id': 'S99'},
    {**REFERENCE, 'type': 'arbitrary'},
    [],
])
def test_invalid_reference_returns_structured_refusal_without_query(api, bad, monkeypatch):
    client, service = api
    def must_not_query(*args, **kwargs):
        raise AssertionError('invalid reference reached tools')
    monkeypatch.setattr(service.tools, 'query_metrics', must_not_query)
    response = ask(client, '这段时间净营业额是多少？', bad)
    assert response.status_code == 200
    body = response.json()
    assert body['answer_type'] == 'refusal' and body['data_evidence'] == []
    assert step(client.get('/api/trace/' + body['trace_id']).json(), 'context_validation')['valid'] is False


def test_rebuild_with_changed_source_follows_new_data(tmp_path):
    source = tmp_path / 'data'
    source.mkdir()
    shutil.copy2(ROOT / 'data/pos.db', source / 'pos.db')
    base = replace(load_settings(), data_dir=source, var_dir=tmp_path / 'var-a',
                   llm_base_url='', llm_api_key='', llm_model='')
    before = Service(base).chat('s', '这段时间净营业额是多少？', REFERENCE)
    with sqlite3.connect(source / 'pos.db') as db:
        rowid, amount = db.execute("SELECT rowid, amount FROM sales WHERE date BETWEEN '2026-06-01' AND '2026-06-30' AND store_id='S02' AND CAST(amount AS REAL)>0 LIMIT 1").fetchone()
        db.execute('UPDATE sales SET amount=? WHERE rowid=?', (str(float(amount) + 1000), rowid))
    after_service = Service(replace(base, var_dir=tmp_path / 'var-b'))
    after = after_service.chat('s', '这段时间净营业额是多少？', REFERENCE)
    a = before['data_evidence'][0]['result']['net_revenue']
    b = after['data_evidence'][0]['result']['net_revenue']
    assert b == a + 1000
    assert str(b) in after['answer']
