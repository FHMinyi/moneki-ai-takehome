"""G3-06 review repair: G3-01 live routing over local controlled HTTP."""
import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'review-r1'
OUT.mkdir(exist_ok=True)
base = os.environ.get('G306_REVIEW_BASE_URL', 'http://127.0.0.1:8038')
model = os.environ.get('G306_REVIEW_MODEL_URL', 'http://127.0.0.1:9036')
question = '预测模型训练前，请查询S02六月牛肉poke净营业额。'
reference = {'type': 'daily_trend', 'start': '2026-06-01', 'end': '2026-06-30',
             'store_id': 'S02', 'metric': 'net_revenue'}
params = {'start': '2026-06-01', 'end': '2026-06-30', 'store_id': 'S02', 'product_id': 'P06'}
results = []
with httpx.Client(timeout=30, trust_env=False) as client:
    client.post(model + '/case', json={'tool': 'query_metrics', 'params': params,
                                       'metric': 'net_revenue'}).raise_for_status()
    for name, context in [('legacy', None), ('trend', reference)]:
        request = {'session_id': 'g306-review-' + name, 'question': question}
        if context:
            request['context'] = context
        response = client.post(base + '/api/chat', json=request)
        response.raise_for_status()
        answer = response.json()
        trace = client.get(base + '/api/trace/' + answer['trace_id']).json()
        expected = client.get(base + '/api/metrics/summary', params=params).json()
        assert answer['answer_type'] == 'data'
        assert len(trace['llm_calls']) == 2
        assert answer['data_evidence'][0]['params'] == params
        assert answer['data_evidence'][0]['result'] == expected
        plan = next(step['detail'] for step in trace['steps'] if step['step'] == 'plan')
        assert plan['kind'] == 'out_of_scope'  # proves model bypassed the old heuristic
        if context:
            resolution = next(step['detail'] for step in trace['steps'] if step['step'] == 'context_resolution')
            assert resolution['effective']['start'] == '2026-06-01'
            assert resolution['effective']['store_id'] == 'S02'
        results.append({'request': request, 'answer': answer, 'trace': trace, 'independent_metrics_api': expected})
(OUT / 'routes.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
print('review live routing HTTP: legacy + trend 2/2; real tool result equals metrics API')
