"""Hand-calculated KB-001 ranking cases, separate from production aggregation."""

import sqlite3

from kbqa.cleaning import build_clean_db
from kbqa.tools import DataTools
from test_cleaning import fixture_db


def test_top_products_ties_refunds_stores_and_names(tmp_path):
    source, clean = tmp_path / "source.db", tmp_path / "clean.db"
    fixture_db(source, [
        ("A", "2026-06-01", "S01", "P01", "2", "10.00", "card"),
        ("B", "2026-06-01", "S01", "P02", "1", "10.00", "card"),
        ("C", "2026-06-01", "S02", "P02", "1", "8.00", "card"),
        ("D", "2026-06-02", "S01", "P01", "1", "-4.00", "card"),
        ("E", "2026-06-01", "S01", "P01", "1", "0.00", "card"),
    ])
    with sqlite3.connect(source) as db:
        db.execute("INSERT INTO stores VALUES ('S02','Second store','C','D')")
        db.execute("UPDATE products SET product_name='Renamed from dimension' WHERE product_id='P02'")
    build_clean_db(source, clean)
    tools = DataTools(clean)
    try:
        tie = tools.top_products("2026-06-01", "2026-06-01", "S01")["products"]
        assert [(p["product_id"], p["net_revenue"], p["qty"]) for p in tie] == [
            ("P01", 10.0, 2), ("P02", 10.0, 1)]
        assert tie[1]["product_name"] == "Renamed from dimension"
        after_refund = tools.top_products("2026-06-01", "2026-06-02", "S01")["products"]
        assert [(p["product_id"], p["net_revenue"], p["qty"]) for p in after_refund] == [
            ("P02", 10.0, 1), ("P01", 6.0, 1)]
        assert tools.top_products("2026-06-01", "2026-06-02", "S02")["products"][0]["net_revenue"] == 8.0
        assert tools.top_products("2027-01-01", "2027-01-31")["products"] == []
    finally:
        tools.close()


def test_top_products_limit_only_matching_rows(tmp_path):
    source, clean = tmp_path / "source.db", tmp_path / "clean.db"
    fixture_db(source, [])
    with sqlite3.connect(source) as db:
        db.executemany("INSERT INTO products VALUES (?,?,?,?)", [
            (f"P{i:02}", f"Product {i}", "C", 999) for i in range(3, 15)])
        db.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?)", [
            (f"O{i}", "2026-06-01", "S01", f"P{i:02}", "1", "1.00", "card") for i in range(1, 15)])
    build_clean_db(source, clean)
    tools = DataTools(clean)
    try:
        items = tools.top_products("2026-06-01", "2026-06-01")["products"]
        assert [p["product_id"] for p in items] == [f"P{i:02}" for i in range(1, 11)]
    finally:
        tools.close()


def test_top_products_api(client):
    response = client.get("/api/metrics/top-products", params={"start": "2026-06-18", "end": "2026-06-18", "store_id": "S02"})
    assert response.status_code == 200
    body = response.json()
    assert body["start"] == body["end"] == "2026-06-18"
    assert body["store_id"] == "S02"
    assert len(body["products"]) <= 10
    assert client.get("/api/metrics/top-products", params={"start": "2026-02-30", "end": "2026-06-18"}).status_code == 400
