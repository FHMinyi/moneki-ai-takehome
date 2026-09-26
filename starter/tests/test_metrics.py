"""Contract fixtures with hand-calculated expectations, never production-generated."""
import json
from pathlib import Path

import pytest
from kbqa.cleaning import build_clean_db
from kbqa.tools import DataTools
from test_cleaning import fixture_db


@pytest.fixture
def metrics(tmp_path):
    source, target = tmp_path/'source.db', tmp_path/'clean.db'
    fixture_db(source, [
        ('A','2026-06-01','S01','P01','2','10.00','card'),
        ('A','2026-06-01','S01','P02','1','5.01','card'),
        ('B','2026-06-01','S01','P01','1','5.00','card'),
        ('A','2026-06-02','S01','P01','1','-3.00','card'),
        ('ZERO','2026-06-01','S01','P01','9','0','card'),
    ])
    build_clean_db(source, target)
    tools = DataTools(target)
    yield tools
    tools.close()


def values(result):
    return {key: result[key] for key in ('net_revenue','refund_amount','orders','aov','qty')}


def test_hand_calculated_sales_and_rounding(metrics):
    # (10 + 5.01 + 5) / two orders = 10.005 -> 10.01; zero amount is not a sale.
    assert values(metrics.query_metrics('2026-06-01','2026-06-01')) == dict(
        net_revenue=20.01, refund_amount=0, orders=2, aov=10.01, qty=4)


def test_refund_own_day_and_combination(metrics):
    assert values(metrics.query_metrics('2026-06-02','2026-06-02','S01','P01')) == dict(
        net_revenue=-3, refund_amount=3, orders=0, aov=None, qty=-1)
    assert values(metrics.query_metrics('2026-06-01','2026-06-02',' s01 ','p01')) == dict(
        net_revenue=12, refund_amount=3, orders=2, aov=6, qty=2)


def test_empty(metrics):
    assert values(metrics.query_metrics('2027-01-01','2027-01-01')) == dict(
        net_revenue=0, refund_amount=0, orders=0, aov=None, qty=0)


def test_daily_shared_boundary(metrics):
    assert metrics.daily_metrics('2026-06-01','2026-06-03')['days'] == [
        dict(date='2026-06-01',net_revenue=20.01,orders=2,aov=10.01),
        dict(date='2026-06-02',net_revenue=-3,orders=0,aov=None),
        dict(date='2026-06-03',net_revenue=0,orders=0,aov=None)]
    assert metrics.daily_metrics('2026-06-02','2026-06-02')['days'][0]['net_revenue'] == -3


PUBLIC = [json.loads(line) for line in (Path(__file__).resolve().parents[2]/'eval/public_questions.jsonl').read_text().splitlines()][:5]
@pytest.mark.parametrize('case', PUBLIC, ids=lambda case: case['id'])
def test_public_metrics(client, case):
    request = case['request']
    response = client.get(request['path'], params=request['params'])
    assert response.status_code == 200
    for key, expected in case['expect'].items():
        actual = response.json()[key]
        assert actual is None if expected['value'] is None else abs(actual-expected['value']) <= expected['tol']


@pytest.mark.parametrize('path', ['/api/metrics/summary','/api/metrics/daily'])
@pytest.mark.parametrize('start,end', [('20260601','2026-06-02'),('2026-W23-1','2026-06-02'),('2026-02-30','2026-06-02'),('2026-06-02','2026-06-01')])
def test_invalid_dates(client, path, start, end):
    response = client.get(path, params=dict(start=start,end=end))
    assert response.status_code == 400
    assert response.json()['error']


def test_store_options(client):
    data = client.get('/api/stores').json()
    assert len(data['stores']) == 5
    assert all(row['store_id'] and row['store_name'] for row in data['stores'])


def test_existing_tool_boundary_regressions(metrics):
    # Existing consumers of _where/query_metrics must include the end day too.
    assert metrics.payment_mix('2026-06-02','2026-06-02')['total_net_revenue'] == -3
    assert metrics.top_products('2026-06-02','2026-06-02')['products'][0]['net_revenue'] == -3
    assert metrics.by_store('2026-06-02','2026-06-02')['stores'][0]['net_revenue'] == -3
    assert metrics.by_store_category('2026-06-02','2026-06-02')['categories'][0]['net_revenue'] == -3
    assert metrics.compare_periods('2026-06-01','2026-06-01','2026-06-02','2026-06-02')['period_b']['net_revenue'] == -3
