"""Real network doc/clarify boundaries through the merged trend scope wrapper."""
import sys,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'docs/verification/g3-02'))
sys.path.insert(0,str(ROOT/'docs/verification/g3-02/review-r1-r2'))
import test_http as h
from test_anchored_selection import anchored,duration
REF={'type':'daily_trend','start':'2026-06-01','end':'2026-06-30','store_id':'S02','metric':'net_revenue'}

@pytest.mark.parametrize('q,doc,needle,amount,as_of,store',[
 ('外卖订单多久内可以申请退款？','KB-013','24','24 小时','2026-09-01','S02'),
 ('2026-06-14 S03 外卖订单多久内可以退款？','KB-012','7 天','7 天','2026-06-14','S03'),
])
def test_referenced_search_preserves_plan_and_document_binding(tmp_path,q,doc,needle,amount,as_of,store):
 with h.runtime(tmp_path,{'query':q,'selector':anchored(doc,needle,('外卖订单','外卖订单'),('退款','退款'),duration('多久',amount))}) as (r,serve,payload):
  with serve() as req:
   a=req('/api/chat',{'session_id':'cross','question':q,'context':REF})
   t=req('/api/trace/'+a['trace_id'])
 assert a['answer_type']=='doc',(a,t['errors'])
 assert not a['data_evidence'] and t['errors']==[]
 assert any(s['step']=='context_resolution' for s in t['steps'])
 evidence=next(c for c in a['citations'] if c.get('evidence_id'))
 assert evidence['scope']['as_of']==as_of and evidence['scope']['store_id']==store
 assert len(t['llm_calls'])==2

@pytest.mark.parametrize('kind',['refusal','clarify'])
def test_referenced_nonfact_states_cannot_deliver_policy(tmp_path,kind):
 with h.runtime(tmp_path,{'query':'外卖退款','content':json.dumps({'answer_type':kind,'answer':'外卖退款不需要顾客出示身份证。请问还需要核对什么？'})}) as (r,serve,payload):
  with serve() as req:
   a=req('/api/chat',{'session_id':'state','question':'外卖退款需要身份证吗？','context':REF})
   t=req('/api/trace/'+a['trace_id'])
 assert a['answer_type']==kind and not a['citations'] and not a['data_evidence']
 assert '身份证' not in a['answer'] and not t['errors']
 assert any(s['step']==('clarification_state' if kind=='clarify' else 'insufficient_evidence') for s in t['steps'])
