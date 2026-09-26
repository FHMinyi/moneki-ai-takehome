"""Compare the live daily endpoint with independent queries over the cleaned ledger."""

import json
import sqlite3
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

BASE = "http://127.0.0.1:8003"
DB = Path("/tmp/moneki-g1-03-var/clean.db")


def get(path, params):
    with urlopen(f"{BASE}{path}?{urlencode(params)}") as response:
        assert response.status == 200
        return json.load(response)


def expected_day(db, day, store_id):
    where = "date = ?" + (" AND store_id = ?" if store_id else "")
    params = (day, store_id) if store_id else (day,)
    rows = db.execute(f"SELECT order_id, amount_cents FROM sales_clean WHERE {where}", params).fetchall()
    cents = sum(row[1] for row in rows)
    orders = len({row[0] for row in rows if row[1] > 0})
    aov = float((Decimal(cents) / 100 / orders).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if orders else None
    return {"date": day, "net_revenue": cents / 100, "orders": orders, "aov": aov}


CASES = [
    ("M06/zero and end day", "2026-06-08", "2026-06-12", "S03"),
    ("single/refund day", "2026-06-04", "2026-06-04", "S02"),
    ("cross month", "2026-06-29", "2026-07-02", None),
    ("empty", "2026-09-01", "2026-09-03", "S01"),
    ("full period", "2026-05-01", "2026-08-31", None),
]

with sqlite3.connect(DB) as db:
    report = []
    for name, start, end, store_id in CASES:
        params = {"start": start, "end": end}
        if store_id:
            params["store_id"] = store_id
        days = get("/api/metrics/daily", params)["days"]
        expected = []
        cursor = date.fromisoformat(start)
        last = date.fromisoformat(end)
        while cursor <= last:
            expected.append(expected_day(db, cursor.isoformat(), store_id))
            cursor += timedelta(days=1)
        assert days == expected, name
        summary = get("/api/metrics/summary", params)
        assert round(sum(day["net_revenue"] for day in days), 2) == summary["net_revenue"], name
        report.append({"case": name, "range": [start, end], "store_id": store_id,
                       "days": len(days), "net_revenue": summary["net_revenue"], "orders": summary["orders"],
                       "sum_daily_orders": sum(day["orders"] for day in days)})
    print(json.dumps(report, ensure_ascii=False, indent=2))
