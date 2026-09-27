"""Network HTTP matrix for explicit fields after an early planner exit."""
import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ.get('G306_REVIEW_EVIDENCE_DIR', str(ROOT / 'review-r2')))
OUT.mkdir(exist_ok=True)
base = os.environ.get('G306_REVIEW_BASE_URL', 'http://127.0.0.1:8040')
model = os.environ.get('G306_REVIEW_MODEL_URL', 'http://127.0.0.1:9036')
reference = {'type': 'daily_trend', 'start': '2026-06-01', 'end': '2026-06-30',
             'store_id': 'S02', 'metric': 'net_revenue'}
records = []


def ask(client, name, question, expected_type, expected_reason=None):
    before = client.get(model).json()['requests']
    payload = {'session_id': 'r2-' + name, 'question': question, 'context': reference}
    response = client.post(base + '/api/chat', json=payload)
    assert response.status_code == 200
    answer = response.json()
    trace = client.get(base + '/api/trace/' + answer['trace_id']).json()
    after = client.get(model).json()['requests']
    assert answer['answer_type'] == expected_type
    assert trace['errors'] == []
    resolution = next(step['detail'] for step in trace['steps'] if step['step'] == 'context_resolution')
    if expected_reason:
        assert resolution.get('rejection', resolution.get('clarification')) == expected_reason
        assert resolution['effective'] is None and after == before
        assert answer['data_evidence'] == []
    else:
        assert after - before == 2
        assert answer['data_evidence']
    records.append({'name': name, 'request': payload, 'response': answer,
                    'trace': trace, 'model_requests_before': before, 'model_requests_after': after})
    return answer, resolution


with httpx.Client(timeout=30, trust_env=False) as client:
    for name, question, kind, reason in [
        ('unknown-store', '预测模型训练前，请查询S99六月净营业额。', 'refusal', 'unknown_store'),
        ('unknown-product', '预测模型训练前，请查询S02 P99六月净营业额。', 'refusal', 'unknown_product'),
        ('now-outside-data', '预测模型训练前，请查询S02现在净营业额。', 'refusal', 'out_of_period'),
        ('two-windows-unspecified', '预测模型训练前，请查询S02六月和七月净营业额。', 'clarify', 'multiple_periods_without_comparison'),
    ]:
        ask(client, name, question, kind, reason)

    period = client.get(base + '/api/health').json()['data_period']
    params = {'start': period['start'], 'end': period['end'], 'store_id': 'S02'}
    client.post(model + '/case', json={'tool': 'query_metrics', 'params': params,
                                       'metric': 'net_revenue'}).raise_for_status()
    answer, resolution = ask(client, 'whole-period',
                             '预测模型训练前，请查询S02全部时间净营业额。', 'data')
    expected = client.get(base + '/api/metrics/summary', params=params).json()
    assert answer['data_evidence'][0]['params'] == params
    assert answer['data_evidence'][0]['result'] == expected
    assert resolution['source']['window'] == 'question'
    records[-1]['independent_metrics_api'] = expected

    compare = {'start_a': '2026-06-01', 'end_a': '2026-06-30',
               'start_b': '2026-07-01', 'end_b': '2026-07-31', 'store_id': 'S02'}
    client.post(model + '/case', json={'tool': 'compare_periods', 'params': compare,
                                       'metric': 'net_revenue'}).raise_for_status()
    answer, resolution = ask(client, 'compare',
                             '预测模型训练前，请比较S02六月和七月净营业额。', 'data')
    result = answer['data_evidence'][0]['result']
    june = client.get(base + '/api/metrics/summary', params={'start': compare['start_a'],
                   'end': compare['end_a'], 'store_id': 'S02'}).json()
    july = client.get(base + '/api/metrics/summary', params={'start': compare['start_b'],
                   'end': compare['end_b'], 'store_id': 'S02'}).json()
    assert answer['data_evidence'][0]['params'] == compare
    assert result['period_a'] == june and result['period_b'] == july
    assert resolution['effective']['compare_window'] == ['2026-07-01', '2026-07-31']
    records[-1]['independent_metrics_api'] = {'period_a': june, 'period_b': july}

(OUT / 'early-plan-http.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
print('early-plan network HTTP: 4 safe stops + 2 data paths; real tools and metrics API agree')
