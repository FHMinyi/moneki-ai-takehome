"""Independent daily/interval expectations for the dashboard's trend endpoint."""

from kbqa.cleaning import build_clean_db
from kbqa.tools import DataTools
from test_cleaning import fixture_db


def test_daily_boundaries_refunds_and_non_additive_orders(tmp_path):
    source, target = tmp_path / "source.db", tmp_path / "clean.db"
    fixture_db(source, [
        ("REUSED", "2026-06-30", "S01", "P01", "1", "10.00", "card"),
        ("REUSED", "2026-07-02", "S01", "P02", "1", "6.00", "card"),
        ("REFUND", "2026-07-02", "S01", "P01", "1", "-20.00", "card"),
    ])
    build_clean_db(source, target)
    tools = DataTools(target)
    try:
        expected = [
            {"date": "2026-06-30", "net_revenue": 10.0, "orders": 1, "aov": 10.0},
            {"date": "2026-07-01", "net_revenue": 0.0, "orders": 0, "aov": None},
            {"date": "2026-07-02", "net_revenue": -14.0, "orders": 1, "aov": -14.0},
        ]
        assert tools.daily_metrics("2026-06-30", "2026-07-02", "S01")["days"] == expected
        assert tools.daily_metrics("2026-07-02", "2026-07-02")["days"] == expected[-1:]
        assert tools.daily_metrics("2026-08-01", "2026-08-02")["days"] == [
            {"date": day, "net_revenue": 0.0, "orders": 0, "aov": None}
            for day in ("2026-08-01", "2026-08-02")
        ]
        interval = tools.query_metrics("2026-06-30", "2026-07-02", "S01")
        assert interval["net_revenue"] == -4.0
        assert sum(day["net_revenue"] for day in expected) == interval["net_revenue"]
        assert sum(day["orders"] for day in expected) == 2
        assert interval["orders"] == 1
        assert interval["aov"] == -4.0
    finally:
        tools.close()
