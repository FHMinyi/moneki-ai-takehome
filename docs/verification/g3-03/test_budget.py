from live_budget import *
import pytest
@pytest.mark.parametrize('limit',[4,5])
def test_chat_limit(limit):
 ledger=dict(chat_count=limit,calls=[])
 assert can_reserve(ledger)==(limit==4)
def test_reserve_unknown_usage_and_limits():
 ledger=dict(chat_count=1,calls=[])
 for i in range(5):
  e=reserve(ledger,250000,0);settle(e,503,None,1)
 assert committed(ledger)==11 and not can_reserve(ledger)
def test_usage_releases_and_attempts_bounded():
 ledger=dict(chat_count=1,calls=[])
 for i in range(14):
  e=reserve(ledger,100,0);assert e['accounted_cny']==2.2;settle(e,200,dict(prompt_tokens=100,completion_tokens=20),1)
 assert abs(committed(ledger)-14*.00036)<1e-9 and not can_reserve(ledger)
