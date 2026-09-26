"""Independent CSV audit: no kbqa imports, no production parser reuse."""
import csv
import json
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

root = Path(__file__).resolve().parents[3]
data = root / 'data'
with (data/'stores.csv').open() as f:
    stores = {r['store_id'] for r in csv.DictReader(f)}
with (data/'products.csv').open() as f:
    products = {r['product_id'] for r in csv.DictReader(f)}
counts = Counter()
seen = set()
raw = 0
with (data/'sales.csv').open() as f:
    for r in csv.DictReader(f):
        raw += 1
        try:
            parts = r['date'].strip().replace('/', '-').split('-')
            a,b,c = map(int, parts)
            day = date(a,b,c) if len(parts[0]) == 4 else date(c,b,a)
        except (ValueError, TypeError):
            counts['1_unparseable_date'] += 1
            continue
        amount = r['amount'].strip().removeprefix('¥').strip()
        if not amount:
            counts['2_empty_amount'] += 1
            continue
        qty = int(r['qty'])
        if qty <= 0:
            counts['3_qty_le_zero'] += 1
            continue
        store, product = r['store_id'].strip().upper(), r['product_id'].strip().upper()
        if store not in stores:
            counts['4_store_not_in_stores'] += 1
            continue
        if product not in products:
            counts['5_product_not_in_products'] += 1
            continue
        row = (r['order_id'], day.isoformat(), store, product, qty, Decimal(amount), r['payment'])
        if row in seen:
            counts['6_duplicate_row'] += 1
        else:
            seen.add(row)
print(json.dumps({'raw_rows':raw, 'kept_rows':len(seen), 'removed':dict(sorted(counts.items())),
                  'period':{'start':min(r[1] for r in seen),'end':max(r[1] for r in seen)}}, indent=2))
