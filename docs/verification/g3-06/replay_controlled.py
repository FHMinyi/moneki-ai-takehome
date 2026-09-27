"""Replay two scoped chats against an isolated local controlled model + real backend."""
import json
import os
from pathlib import Path
import httpx

root = Path(__file__).resolve().parent
backend = os.environ.get('G306_BASE_URL', 'http://127.0.0.1:8037')
model = os.environ.get('G306_MODEL_URL', 'http://127.0.0.1:9036')
client = httpx.Client(timeout=30, trust_env=False)
reference = {'type': 'daily_trend', 'start': '2026-06-01', 'end': '2026-06-30',
             'store_id': 'S02', 'metric': 'net_revenue'}
cases = [
    ('这段时间净营业额是多少？', {'start': '2026-06-01', 'end': '2026-06-30', 'store_id': 'S02', 'product_id': None}),
    ('7月 S01 的净营业额是多少？', {'start': '2026-07-01', 'end': '2026-07-31', 'store_id': 'S01', 'product_id': None}),
]
records = []
for question, params in cases:
    client.post(model + '/case', json={'tool': 'query_metrics', 'params': params, 'metric': 'net_revenue'}).raise_for_status()
    payload = {'session_id': 'g306-controlled', 'question': question, 'context': reference}
    response = client.post(backend + '/api/chat', json=payload)
    response.raise_for_status()
    answer = response.json()
    trace = client.get(backend + '/api/trace/' + answer['trace_id']).json()
    expected = client.get(backend + '/api/metrics/summary', params={k: v for k, v in params.items() if v is not None}).json()
    assert answer['answer_type'] == 'data', answer
    assert answer['data_evidence'][0]['result'] == expected
    assert answer['data_evidence'][0]['params'] == params
    assert any(s['step'] == 'tool' and s['detail']['result'] == expected for s in trace['steps'])
    assert any(s['step'] == 'context_resolution' for s in trace['steps'])
    records.append({'request': payload, 'answer': answer, 'trace': trace, 'expected': expected})
(root / 'controlled-http.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
print('controlled HTTP: 2/2; real business tool result equals independent metrics API')
