"""KB-001 behavior expectations are hand-authored, independent of production parsers."""
import hashlib
import sqlite3
from pathlib import Path

import pytest
from kbqa.cleaning import build_clean_db, open_readonly
from kbqa.tools import DataTools

SOURCE = Path(__file__).resolve().parents[2] / 'data/pos.db'
REASONS = ['1_unparseable_date', '2_empty_amount', '3_qty_le_zero',
           '4_store_not_in_stores', '5_product_not_in_products', '6_duplicate_row']


def fixture_db(path, rows):
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE stores(store_id,store_name,category,district);'
                         'CREATE TABLE products(product_id,product_name,product_category,unit_price);'
                         'CREATE TABLE sales(order_id,date,store_id,product_id,qty,amount,payment);'
                         "INSERT INTO stores VALUES ('S01','Store','C','D');"
                         "INSERT INTO products VALUES ('P01','One','C',999),('P02','Two','C',999);")
        db.executemany('INSERT INTO sales VALUES (?,?,?,?,?,?,?)', rows)


def test_normalization_refunds_multiline_and_priority(tmp_path):
    rows = [
        ('A','25-07-2026',' s01 ','p01 ','2',' ¥38.00 ','card'),
        ('A','2026/7/25','S01','P02','1','20','card'),
        ('R','07-06-2026','S01','P01','1','-38.00','card'),
        ('A','2026-07-25','S01','P01','2','38.00','card'),
        ('bad','N/A','bad','bad','0','','card'),
        ('bad','2026-06-01','bad','bad','0','  ','card'),
        ('bad','2026-06-01','bad','bad','0','10','card'),
        ('bad','2026-06-01','bad','bad','1','10','card'),
        ('bad','2026-06-01','S01','bad','1','10','card'),
    ]
    source, target = tmp_path/'source.db', tmp_path/'clean.db'
    fixture_db(source, rows)
    report = build_clean_db(source, target)
    assert report.kept_rows == 3
    assert report.removed == dict.fromkeys(REASONS, 1)
    with sqlite3.connect(target) as db:
        assert db.execute('SELECT * FROM sales_clean ORDER BY rowid').fetchall() == [
            ('A','2026-07-25','S01','P01',2,3800,'card',0),
            ('A','2026-07-25','S01','P02',1,2000,'card',0),
            ('R','2026-06-07','S01','P01',1,-3800,'card',1)]
    assert report.raw_rows == report.kept_rows + sum(report.removed.values())


def test_sample_rebuild_is_repeatable_and_source_unchanged(tmp_path):
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    snapshots = []
    for _ in range(2):
        target = tmp_path/'clean.db'
        report = build_clean_db(SOURCE, target)
        assert report.raw_rows == 18628
        assert report.kept_rows == 18290
        assert sum(report.removed.values()) == 338
        assert report.removed == dict(zip(REASONS, [8, 150, 30, 10, 40, 100]))
        tools = DataTools(target)
        assert tools.valid_sales_rows() == report.kept_rows
        assert tools.data_period() == {'start':'2026-05-01','end':'2026-08-31'}
        snapshots.append((report.as_dict(), tools.conn.execute('SELECT * FROM sales_clean').fetchall()))
        tools.close()
    assert snapshots[0] == snapshots[1]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before


def test_empty_and_readonly(tmp_path):
    source, target = tmp_path/'source.db', tmp_path/'clean.db'
    fixture_db(source, [])
    assert build_clean_db(source, target).kept_rows == 0
    tools = DataTools(target)
    assert tools.data_period() == {'start':None,'end':None}
    tools.close()
    conn = open_readonly(source)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute('DELETE FROM sales')
    conn.close()


def test_source_cannot_be_target(tmp_path):
    source = tmp_path/'source.db'
    fixture_db(source, [])
    before = source.read_bytes()
    with pytest.raises(ValueError):
        build_clean_db(source, source)
    assert source.read_bytes() == before


@pytest.mark.parametrize('day', ['2026-02-30', '31-06-2026', '', None, 'N/A'])
def test_invalid_calendar_dates_removed(tmp_path, day):
    source, target = tmp_path/'source.db', tmp_path/'clean.db'
    fixture_db(source, [('A',day,'S01','P01','1','10','card')])
    report = build_clean_db(source, target)
    assert report.kept_rows == 0
    assert report.removed == dict(zip(REASONS, [1, 0, 0, 0, 0, 0]))


def test_unruled_amount_fails_without_replacing_existing_result(tmp_path):
    source, target = tmp_path/'source.db', tmp_path/'clean.db'
    fixture_db(source, [('A','2026-06-01','S01','P01','1','10','card')])
    build_clean_db(source, target)
    before = target.read_bytes()
    with sqlite3.connect(source) as db:
        db.execute("UPDATE sales SET amount='not money'")
    with pytest.raises(ValueError, match='Nonempty amount'):
        build_clean_db(source, target)
    assert target.read_bytes() == before


def test_zero_amount_and_unmodified_identity_fields(tmp_path):
    source, target = tmp_path/'source.db', tmp_path/'clean.db'
    fixture_db(source, [('A','2026-06-01','S01','P01','1','0','card'),
                        (' A','2026-06-01','S01','P01','1','0','card'),
                        ('A','2026-06-01','S01','P01','1','0',' card')])
    report = build_clean_db(source, target)
    assert report.kept_rows == 3  # KB-001 normalizes only its four specified fields.
    assert report.kept_sales_rows == report.kept_refund_rows == 0


def test_whitespace_amount_and_noninteger_quantity(tmp_path):
    source, target = tmp_path/'source.db', tmp_path/'clean.db'
    fixture_db(source, [('A','2026-06-01','S01','P01','1','\n\r ','card'),
                        ('B','2026-06-01','S01','P01','1.5','10','card')])
    report = build_clean_db(source, target)
    assert report.kept_rows == 0
    assert report.removed == dict(zip(REASONS, [0, 1, 1, 0, 0, 0]))
