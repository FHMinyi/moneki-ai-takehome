"""Independent row-by-row audit against the running G1-04 API."""
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path

DB = Path(os.environ.get('G1_04_DB', '/tmp/moneki-g1-04-var/clean.db'))
BASE = os.environ.get('G1_04_BASE_URL', 'http://127.0.0.1:8004') + '/api/metrics/top-products'


def check(start, end, store_id=None):
    with sqlite3.connect(DB) as db:
        names = dict(db.execute('SELECT product_id, product_name FROM products'))
        buckets = {}
        for day, store, product, qty, cents in db.execute(
            'SELECT date, store_id, product_id, qty, amount_cents FROM sales_clean'
        ):
            if not start <= day <= end or (store_id and store != store_id):
                continue
            item = buckets.setdefault(product, [0, 0])
            item[0] += cents
            item[1] += qty if cents > 0 else -qty if cents < 0 else 0
    expected = sorted(buckets, key=lambda p: (-buckets[p][0], p))[:10]
    params = urllib.parse.urlencode(dict(start=start, end=end, **({'store_id': store_id} if store_id else {})))
    with urllib.request.urlopen(f'{BASE}?{params}') as response:
        actual = json.load(response)['products']
    assert len(actual) == len(expected)
    for row, product in zip(actual, expected):
        assert (row['product_id'], row['product_name'], round(row['net_revenue'] * 100), row['qty']) == (
            product, names[product], buckets[product][0], buckets[product][1]
        )
    return {'filter': {'start': start, 'end': end, 'store_id': store_id},
            'matched_products': len(buckets), 'top_ids': expected,
            'top_cents': [buckets[p][0] for p in expected]}


if __name__ == '__main__':
    cases = [
        check('2026-06-18', '2026-06-18', 'S02'),
        check('2026-06-18', '2026-06-18'),
        check('2026-06-01', '2026-06-30', 'S01'),
        check('2026-09-01', '2026-09-30'),
    ]
    print(json.dumps({'status': 'passed', 'cases': cases}, ensure_ascii=False, indent=2))
