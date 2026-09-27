"""Offline checks: no credential import or provider request."""
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from live_budget import RESERVE_CNY, can_reserve, committed, reserve, settle


def ledger(chat=1):
    return {'chat_count': chat, 'calls': []}


def test_reserve_before_outbound_and_complete_usage_release():
    state = ledger()
    outbound = Mock()
    entry = reserve(state, 30000, 1.0)
    assert committed(state) == RESERVE_CNY
    outbound()
    outbound.assert_called_once()
    settle(entry, 200, {'prompt_tokens': 1000, 'completion_tokens': 500}, 2.0)
    assert entry['accounted_cny'] == pytest.approx((1000*2+500*8)/1_000_000)
    assert committed(state) < RESERVE_CNY


@pytest.mark.parametrize('usage', [None, {}, {'prompt_tokens': 4}, {'prompt_tokens': -1, 'completion_tokens': 2}])
def test_unknown_or_incomplete_usage_keeps_full_reserve(usage):
    state = ledger()
    entry = reserve(state, 100, 1.0)
    settle(entry, 503, usage, 2.0)
    assert committed(state) == RESERVE_CNY
    assert 'reserve retained' in entry['note']


def test_insufficient_remaining_balance_prevents_outbound():
    state = ledger()
    outbound = Mock()
    for _ in range(2):
        reserve(state, 100, 1.0)
    assert committed(state) == 4.40
    assert not can_reserve(state)
    with pytest.raises(ValueError, match='outbound request forbidden'):
        reserve(state, 100, 2.0)
    if can_reserve(state):
        outbound()
    outbound.assert_not_called()
    assert len(state['calls']) == 2


def test_attempt_limit_is_per_chat_and_budget_is_global():
    state = ledger()
    for _ in range(6):
        entry = reserve(state, 100, 1.0)
        settle(entry, 200, {'prompt_tokens': 0, 'completion_tokens': 0}, 0.1)
    assert not can_reserve(state)
    state['chat_count'] = 2
    assert can_reserve(state)
