"""Independent raw CSV normalization and decimal aggregation; no production imports.
Run from any directory: python3 docs/verification/g1-02/audit_api.py
Service must be on 8002. M01-M05 expected values remain in test data only.
"""
import contextlib
import io
import json
import runpy
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

root = Path(__file__).resolve().parents[3]
with contextlib.redirect_stdout(io.StringIO()):
    audited = runpy.run_path(str(root/'docs/verification/g1-01/audit_sample.py'))
rows = audited['seen']  # independent normalization of raw CSV, already G1-01 audited
cases = [json.loads(line) for line in (root/'eval/public_questions.jsonl').read_text().splitlines()][:5]
cases += [dict(id='single-day-all',request=dict(params=dict(start='2026-06-18',end='2026-06-18'))),
          dict(id='single-day-store',request=dict(params=dict(start='2026-06-18',end='2026-06-18',store_id='S02'))),
          dict(id='full-range',request=dict(params=dict(start='2026-05-01',end='2026-08-31')))]
results = []
for case in cases:
    params = case['request']['params']
    selected = [r for r in rows if params['start'] <= r[1] <= params['end'] and
                ('store_id' not in params or r[2] == params['store_id']) and
                ('product_id' not in params or r[3] == params['product_id'])]
    net = sum((r[5] for r in selected), Decimal(0))
    refunds = -sum((r[5] for r in selected if r[5] < 0), Decimal(0))
    orders = len({r[0] for r in selected if r[5] > 0})
    expected = dict(net_revenue=float(net),refund_amount=float(refunds),orders=orders,
                    aov=float((net/orders).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) if orders else None,
                    qty=sum(r[4] * (1 if r[5] > 0 else -1 if r[5] < 0 else 0) for r in selected))
    url = 'http://127.0.0.1:8002/api/metrics/summary?' + urlencode(params)
    actual = json.load(urlopen(url))
    assert all(actual[k] == v for k,v in expected.items()), (case['id'],expected,actual)
    results.append(dict(id=case['id'],url=url,independent=expected,api=actual,passed=True))
print(json.dumps(results,ensure_ascii=False,indent=2))
