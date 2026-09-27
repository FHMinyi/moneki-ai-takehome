"""No provider calls: request cap and worst-case reservation math."""
import sys
from pathlib import Path
from decimal import Decimal
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'starter'))
from kbqa import llm

@pytest.mark.parametrize('value',[1,4096,8192])
def test_valid_limits(value):assert llm.valid_output_limit(value)
@pytest.mark.parametrize('value',[None,True,False,0,-1,8193,100000,8192.0,'8192'])
def test_reject_unbounded_or_noninteger(value):assert not llm.valid_output_limit(value)

def test_request_and_conservative_reserve(monkeypatch):
 client=llm.LLMClient('http://offline.invalid','dummy','deepseek-flash')
 body=client._body([],None)
 assert body['max_tokens']==8192
 assert 'thinking' not in body and 'reasoning_effort' not in body
 worst=(Decimal(1048576)*2+Decimal(body['max_tokens'])*8)/1000000
 assert worst==Decimal('2.162688') and worst < Decimal('2.20')
 monkeypatch.setattr(llm,'MAX_TOKENS',8193)
 with pytest.raises(llm.LLMError,match='configuration'):client._body([],None)
