"""Controlled choices exercise real tools/retrieval; not model semantic evidence."""
import json, sys
from pathlib import Path
from dataclasses import replace
from unittest.mock import Mock
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'starter'))
from kbqa.config import load_settings
from kbqa.service import Service
from kbqa.live import LiveEngine
from kbqa.llm import LLMReply, LLMError
from kbqa.trace import Trace
QUESTIONS={q['id']:q['turns'][0]['question'] for q in map(json.loads,(ROOT/'eval/public_questions.jsonl').read_text().splitlines()) if 'turns' in q}
CASES={
'H01':dict(mode='anomaly',tool='compare_periods',params=dict(start_a='2026-06-01',end_a='2026-06-07',start_b='2026-06-08',end_b='2026-06-14',store_id='S03'),metric='net_revenue',doc='KB-020',needle='停业 4 天',role='reason',expected='3,630'),
'H02':dict(mode='target',tool='query_metrics',params=dict(start='2026-06-18',end='2026-06-18',store_id='S02',product_id='P06'),metric='qty',doc='KB-023',needle='当天牛肉poke 目标销量',role='target',expected='125'),
'H03':dict(mode='target',tool='query_metrics',params=dict(start='2026-08-01',end='2026-08-31',product_id='P21'),metric='qty',doc='KB-028',needle='全门店合计目标销量',role='target',expected='689'),
'H04':dict(mode='price',tool='unit_price_check',params=dict(product_id='P06',start='2026-05-01',end='2026-08-31'),metric='unit_price',doc='KB-025',needle='调整为',role='price',expected='45'),
'H05':dict(mode='payment',tool='payment_mix',params=dict(start='2026-08-03',end='2026-08-03',store_id='S05'),metric='share_orders',doc='KB-027',needle='订单全部以现金结算',role='reason',expected='100.00%'),
'H06':dict(mode='anomaly',tool='query_metrics',params=dict(start='2026-08-17',end='2026-08-19',store_id='S02'),metric='net_revenue',doc=None,expected='0.00'),
}
@pytest.fixture(scope='module')
def service(tmp_path_factory):
 return Service(replace(load_settings(),var_dir=tmp_path_factory.mktemp('g303'),llm_api_key='',llm_base_url='',llm_model=''))

def choose(case,items):
 facts=[]
 if case.get('doc'):
  candidates=[e for e in items if e['doc_id']==case['doc'] and case['needle'] in e['quote']]
  assert candidates,(case,[(e['doc_id'],e['quote']) for e in items])
  e=min(candidates,key=lambda e:len(e['quote']))
  facts=[dict(evidence_id=e['evidence_id'],role=case['role'])]
 return dict(answer_type='hybrid',mode=case['mode'],results=[dict(call_id='db',metric=case['metric'])],facts=facts)

def run(service,question,case,mutate=None,reverse=False,repeated=False):
 calls=[dict(id='db',type='function',function=dict(name=case['tool'],arguments=json.dumps(case['params']))),dict(id='kb',type='function',function=dict(name='search_kb',arguments=json.dumps(dict(query=question,top_k=10))))]
 if reverse:calls.reverse()
 client=Mock();rounds=[]
 def respond(messages,*args,**kwargs):
  if not rounds or repeated and len(rounds)==1:
   batch=calls if not rounds else [dict(id='kb2',type='function',function=dict(name='search_kb',arguments=json.dumps(dict(query='退款制度',top_k=5))))]
   rounds.append(1);return LLMReply(dict(role='assistant',content='',tool_calls=batch),'tool_calls','',batch,0)
  items=[e for t in messages if t['role']=='tool' for e in json.loads(t['content'])['result'].get('evidence',[])]
  p=choose(case,items)
  if mutate:p=mutate(p,items)
  content=json.dumps(p);return LLMReply(dict(role='assistant',content=content),'stop',content,[],0)
 client.chat_with_retry.side_effect=respond
 trace=Trace('controlled-g303',question)
 a=LiveEngine(client,service.answerer,service.run_tool,'2026-09-01',service.data_period).answer(service.planner.plan(question),trace,[])
 return a,trace

@pytest.mark.parametrize('qid',CASES)
def test_six_mixed_behaviors(service,qid):
 a,t=run(service,QUESTIONS[qid],CASES[qid])
 assert a.answer_type==('data' if qid=='H06' else 'hybrid'),a
 assert CASES[qid]['expected'] in a.answer,a
 assert a.data_evidence
 if qid=='H06':assert not a.citations and '未找到' in a.answer
 else:assert any(c['doc_id']==CASES[qid]['doc'] for c in a.citations)
 if qid=='H02':assert '已达标' in a.answer and '5' in a.answer
 if qid=='H03':assert '未达标' in a.answer and '211' in a.answer
