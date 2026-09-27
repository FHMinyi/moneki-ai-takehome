"""The G3-04 external-call guard reserves before every actual attempt."""
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("g304_budget", Path(__file__).with_name("live_budget.py"))
budget = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(budget)


def test_reservation_and_unknown_usage_retain_full_liability():
    ledger = {"chat_count": 1, "calls": []}
    entry = budget.reserve(ledger, 30000, 1.0)
    assert entry["accounted_cny"] == 2.20
    budget.settle(entry, "transport_error", None, .1)
    assert budget.committed(ledger) == 2.20
    for _ in range(3):
        budget.settle(budget.reserve(ledger, 1, 2.0), "transport_error", None, .1)
    assert budget.committed(ledger) == 8.80
    assert not budget.can_reserve(ledger)


def test_usage_settles_at_peak_cache_miss_price():
    ledger = {"chat_count": 3, "calls": []}
    entry = budget.reserve(ledger, 100, 1.0)
    budget.settle(entry, 200, {"prompt_tokens": 3000, "completion_tokens": 500}, .2)
    assert entry["accounted_cny"] == .010
    assert budget.PREVIOUS_STAGE_ESTIMATE_CNY + budget.committed(ledger) < budget.STAGE_LIMIT_CNY
    ledger["chat_count"] = 4
    assert not budget.can_reserve(ledger)
