"""把原始 sales 导进 var/clean.db，指标都查这张表。"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Optional

REMOVAL_REASONS = (
    "1_unparseable_date",
    "2_empty_amount",
    "3_qty_le_zero",
    "4_store_not_in_stores",
    "5_product_not_in_products",
    "6_duplicate_row",
)


def parse_amount(value: Optional[str]) -> tuple[Optional[int], str]:
    """返回 (分, 状态)。状态取值：`ok`、`empty`、`bad`。

    KB-001 §2.3 与 §3.2：`¥38.00` 与 `38.00` 是同一个金额；空金额直接剔除，**不回填**。
    """
    text = (value or "").strip().removeprefix("¥").strip()
    if not text:
        return None, "empty"
    try:
        cents = int((Decimal(text) * 100).to_integral_value())
    except (InvalidOperation, ValueError, OverflowError):
        return None, "bad"
    return cents, "ok"


def parse_qty(value: Optional[str]) -> Optional[int]:
    """KB-001 §2.4：按整数解析。解析不了的按 0 处理，会被 §3.3 剔除。"""
    text = (value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except (InvalidOperation, ValueError, OverflowError):
        return None


@dataclass
class CleaningReport:
    raw_rows: int = 0
    kept_rows: int = 0
    kept_sales_rows: int = 0
    kept_refund_rows: int = 0
    removed: dict[str, int] = field(default_factory=lambda: {k: 0 for k in REMOVAL_REASONS})

    def as_dict(self) -> dict:
        return {
            "raw_rows": self.raw_rows,
            "removed": dict(self.removed),
            "removed_rows": sum(self.removed.values()),
            "kept_rows": self.kept_rows,
            "kept_sales_rows": self.kept_sales_rows,
            "kept_refund_rows": self.kept_refund_rows,
        }


def open_readonly(path: Path) -> sqlite3.Connection:
    """以 SQLite 强制只读模式打开数据库。"""
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_date(value: Optional[str]) -> Optional[str]:
    text = (value or "").strip()
    for pattern, fmt in ((r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
                         (r"\d{4}/\d{1,2}/\d{1,2}", "%Y/%m/%d"),
                         (r"\d{2}-\d{2}-\d{4}", "%d-%m-%Y")):
        if re.fullmatch(pattern, text):
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                return None
    return None


def clean_rows(rows: Iterable[sqlite3.Row], store_ids: set[str],
               product_ids: set[str]) -> tuple[list[tuple], CleaningReport]:
    """KB-001: normalize first; count only the first applicable removal reason."""
    report = CleaningReport()
    kept: list[tuple] = []
    seen: set[tuple] = set()
    for row in rows:
        report.raw_rows += 1
        day = normalize_date(row["date"])
        cents, status = parse_amount(row["amount"])
        qty = parse_qty(row["qty"]) or 0
        store = (row["store_id"] or "").strip().upper()
        product = (row["product_id"] or "").strip().upper()
        normalized = (row["order_id"], day, store, product, qty, cents, row["payment"])
        reason = None
        if day is None:
            reason = REMOVAL_REASONS[0]
        elif status == "empty":
            reason = REMOVAL_REASONS[1]
        elif qty <= 0:
            reason = REMOVAL_REASONS[2]
        elif store not in store_ids:
            reason = REMOVAL_REASONS[3]
        elif product not in product_ids:
            reason = REMOVAL_REASONS[4]
        elif normalized in seen:
            reason = REMOVAL_REASONS[5]
        if reason:
            report.removed[reason] += 1
            continue
        if status != "ok":
            # KB-001 has no rule for nonempty, nonnumeric amounts. Fail the
            # rebuild instead of inventing a seventh removal rule or money.
            raise ValueError("Nonempty amount cannot be parsed; source row %d" % report.raw_rows)
        seen.add(normalized)
        kept.append((*normalized, int(cents < 0)))
    report.kept_rows = len(kept)
    report.kept_refund_rows = sum(row[-1] for row in kept)
    report.kept_sales_rows = sum(row[5] > 0 for row in kept)
    return kept, report


_SCHEMA = """
CREATE TABLE stores (store_id TEXT PRIMARY KEY, store_name TEXT, category TEXT, district TEXT);
CREATE TABLE products (product_id TEXT PRIMARY KEY, product_name TEXT,
                       product_category TEXT, unit_price REAL);
CREATE TABLE sales_clean (
    order_id TEXT, date TEXT, store_id TEXT, product_id TEXT,
    qty INTEGER, amount_cents INTEGER, payment TEXT, is_refund INTEGER
);
CREATE INDEX idx_clean_date ON sales_clean(date);
CREATE INDEX idx_clean_store ON sales_clean(store_id);
CREATE INDEX idx_clean_product ON sales_clean(product_id);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
"""


def build_clean_db(source: Path, target: Path) -> CleaningReport:
    """从只读的源库重建清洗表。返回清洗台账，供 `/api/health` 与数据质量面板使用。"""
    if source.resolve() == target.resolve() or (target.exists() and source.samefile(target)):
        raise ValueError("Source and generated database must be separate")
    if not source.exists():
        raise FileNotFoundError("找不到源数据库：%s" % source)
    src = open_readonly(source)
    try:
        stores = [tuple(r) for r in src.execute("SELECT store_id, store_name, category, district FROM stores")]
        products = [
            tuple(r)
            for r in src.execute(
                "SELECT product_id, product_name, product_category, unit_price FROM products"
            )
        ]
        rows, report = clean_rows(
            src.execute("SELECT order_id, date, store_id, product_id, qty, amount, payment FROM sales"),
            {r[0] for r in stores}, {r[0] for r in products}
        )
    finally:
        src.close()

    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="clean-", suffix=".db", dir=target.parent)
    os.close(fd)
    out = sqlite3.connect(temporary)
    try:
        out.executescript(_SCHEMA)
        out.executemany("INSERT INTO stores VALUES (?,?,?,?)", stores)
        out.executemany("INSERT INTO products VALUES (?,?,?,?)", products)
        out.executemany("INSERT INTO sales_clean VALUES (?,?,?,?,?,?,?,?)", rows)
        out.execute(
            "INSERT INTO meta VALUES ('cleaning_report', ?)",
            (json.dumps(report.as_dict(), ensure_ascii=False),),
        )
        out.execute("INSERT INTO meta VALUES ('source_db', ?)", (source.name,))
        out.commit()
    except BaseException:
        out.close()
        Path(temporary).unlink(missing_ok=True)
        raise
    else:
        out.close()
        os.replace(temporary, target)
    return report
