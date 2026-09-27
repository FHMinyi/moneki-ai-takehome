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
'H01':dict(mode='anomaly',tool='compare_periods',params=dict(start_a='2026-06-01',end_a='2026-06-07',start_b='2026-06-08',end_b='2026-06-14',store_id='S03'),metric='net_revenue',doc='KB-020',needle='停业 4 天',role='reason',expected='3630.00'),
'H02':dict(mode='target',tool='query_metrics',params=dict(start='2026-06-18',end='2026-06-18',store_id='S02',product_id='P06'),metric='qty',doc='KB-023',needle='当天牛肉poke 目标销量',role='target',expected='125'),
'H03':dict(query='冷萃乌龙茶首月目标销量',mode='target',tool='query_metrics',params=dict(start='2026-08-01',end='2026-08-31',product_id='P21'),metric='qty',doc='KB-028',needle='全门店合计目标销量',role='target',expected='689'),
'H04':dict(mode='price',tool='unit_price_check',params=dict(product_id='P06',start='2026-05-01',end='2026-08-31'),metric='unit_price',doc='KB-025',needle='调整为',role='price',expected='45'),
'H05':dict(mode='payment',tool='payment_mix',params=dict(start='2026-08-03',end='2026-08-03',store_id='S05'),metric='share_orders',doc='KB-027',needle='全程只收现金',role='reason',expected='100.00%'),
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
 calls=[dict(id='db',type='function',function=dict(name=case['tool'],arguments=json.dumps(case['params']))),dict(id='kb',type='function',function=dict(name='search_kb',arguments=json.dumps(dict(query=case.get('query',question),top_k=10))))]
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

@pytest.mark.parametrize('qid',CASES)
def test_order_repeated_unrelated_search(service,qid):
 a,_=run(service,QUESTIONS[qid],CASES[qid],reverse=True,repeated=True)
 assert a.answer_type==('data' if qid=='H06' else 'hybrid')
 assert CASES[qid]['expected'] in a.answer

@pytest.mark.parametrize('mutate',[
 lambda p,e:{**p,'answer':'达标了，全部数字由模型计算'},
 lambda p,e:{**p,'results':[dict(call_id='db',metric='net_revenue')]},
 lambda p,e:{**p,'results':[dict(call_id='not-executed',metric='qty')]},
 lambda p,e:{**p,'facts':[dict(evidence_id='doc-forged',role='target')]},
 lambda p,e:{**p,'facts':[dict(evidence_id=p['facts'][0]['evidence_id'],role='reason')]},
 lambda p,e:{**p,'operator':'target_minus_actual'},
])
def test_wrong_candidates_rejected(service,mutate):
 with pytest.raises(LLMError):run(service,QUESTIONS['H02'],CASES['H02'],mutate=mutate)

@pytest.mark.parametrize('field,value',[('product_id','P05'),('store_id','S01'),('start','2026-06-17'),('end','2026-06-19')])
def test_wrong_query_scope(service,field,value):
 case={**CASES['H02'],'params':{**CASES['H02']['params'],field:value}}
 with pytest.raises(LLMError):run(service,QUESTIONS['H02'],case)

def test_reversed_comparison(service):
 c=CASES['H01'];p=c['params'];case={**c,'params':{**p,'start_a':p['start_b'],'end_a':p['end_b'],'start_b':p['start_a'],'end_b':p['end_a']}}
 with pytest.raises(LLMError):run(service,QUESTIONS['H01'],case)

def independent_service(tmp_path,qty=7,target=10,extra='',date_value='2026-06-18',product='P06',goal_unit='份'):
 import shutil,sqlite3
 data=tmp_path/'data';data.mkdir();shutil.copy(ROOT/'data/pos.db',data/'pos.db')
 con=sqlite3.connect(data/'pos.db');con.execute('DELETE FROM sales')
 con.executemany('INSERT INTO sales VALUES (?,?,?,?,?,?,?)',[
 ('NEW1','2026-06-18','S02','P06',str(qty),'210.00','现金'),
 ('NEW2','2026-06-18','S02','P06','2','-60.00','现金'),
 ('ZERO','2026-06-18','S02','P06','4','0','银行卡'),
 ('RANGE1','2026-05-01','S01','P01','1','1','现金'),
 ('RANGE2','2026-08-31','S01','P01','1','1','现金')]);con.commit();con.close()
 kb=tmp_path/'kb';kb.mkdir();shutil.copy(ROOT/'knowledge_base/handbook/KB-003_商品与门店别名词典.md',kb)
 name=next(p['product_name'] for p in Service(replace(load_settings(),var_dir=tmp_path/'catalog',llm_api_key='')).catalog.products if p['product_id']==product)
 (kb/'KB-981.md').write_text(f'---\ntitle: {name} 活动计划\neffective_from: {date_value}\nstores: [S02]\n---\n# {name} 活动计划\n\n当天{name}目标销量 {target} {goal_unit}。\n\n'+extra)
 s=Service(replace(load_settings(),data_dir=data,kb_dir=kb,var_dir=tmp_path/'var',llm_api_key='',llm_base_url='',llm_model=''))
 s.rebuild();return s

@pytest.mark.parametrize('qty,target,expected,met',[(7,10,5,False),(17,10,15,True),(17,21,15,False),(12,10,10,True)])
def test_replaced_database_and_target_cross_boundary(tmp_path,qty,target,expected,met):
 s=independent_service(tmp_path,qty,target)
 c={**CASES['H02'],'doc':'KB-981','needle':'目标销量'}
 a,t=run(s,QUESTIONS['H02'],c)
 assert a.answer_type=='hybrid'
 # Independent oracle: one positive sale, one refund; zero amount contributes no qty.
 assert a.data_evidence[0]['result']['qty']==expected==qty-2
 calc=a.data_evidence[0]['calculations'][0]
 assert calc['result']==expected-target and calc['met']==met
 assert calc['target']['value']==target
 assert ('已达标' if met else '未达标') in a.answer
 assert a.citations[0]['quote'] in s.index.texts['KB-981']

@pytest.mark.parametrize('kind',['wrong-date','wrong-product','wrong-unit'])
def test_replaced_bad_target(tmp_path,kind):
 kwargs={'date_value':'2026-06-17'} if kind=='wrong-date' else {'product':'P05'} if kind=='wrong-product' else {'goal_unit':'元'}
 s=independent_service(tmp_path,**kwargs)
 c={**CASES['H02'],'doc':'KB-981','needle':'目标销量','query':'活动计划目标销量'}
 with pytest.raises(LLMError):run(s,QUESTIONS['H02'],c)

def test_payment_zero_amount_not_order(tmp_path):
 s=independent_service(tmp_path)
 result=s.run_tool('payment_mix',dict(start='2026-06-18',end='2026-06-18',store_id='S02'))
 assert result['total_orders']==1 and result['payments']['银行卡']['orders']==0
 assert result['payments']['现金']['share_orders']==1

@pytest.mark.parametrize('denominator',['share_orders','share_revenue'])
def test_payment_independent_ratio(tmp_path,denominator):
 import sqlite3
 s=independent_service(tmp_path)
 con=sqlite3.connect(s.settings.source_db)
 con.execute('INSERT INTO sales VALUES (?,?,?,?,?,?,?)',('CARD','2026-06-18','S02','P06','1','50','银行卡'));con.commit();con.close()
 s.tools.close();s.rebuild()
 c=dict(mode='payment',tool='payment_mix',params=dict(start='2026-06-18',end='2026-06-18',store_id='S02'),metric=denominator,doc=None)
 q='6月18日S02现金支付'+('金额' if denominator=='share_revenue' else '订单')+'占比是多少，为什么？'
 a,t=run(s,q,c)
 calc=a.data_evidence[0]['calculations'][0]
 assert calc['result']==(50.0 if denominator=='share_orders' else 75.0)
 assert not a.citations

def test_zero_with_old_unrelated_event_is_rejected(tmp_path):
 s=independent_service(tmp_path,extra='S02 在2026-06-18因网络故障停业。')
 c={**CASES['H06'],'doc':'KB-981','needle':'网络故障','role':'reason','query':'S02网络故障停业'}
 with pytest.raises(LLMError,match='事件日期'):run(s,QUESTIONS['H06'],c)

def test_cannot_exchange_order_and_revenue_share(service):
 q='8月3日S05现金支付金额占比是多少，为什么？'
 with pytest.raises(LLMError,match='金额占比'):run(service,q,CASES['H05'])

def test_missing_or_failed_search_never_means_unknown(service):
 from kbqa.mixed_answer import render_mixed
 from kbqa.document_evidence import DocumentEvidence
 c=CASES['H06'];ev=[dict(_call_id='db',tool=c['tool'],params=c['params'],result=service.run_tool(c['tool'],c['params']))]
 for searched,failures in [(False,[]),(True,[dict(tool='search_kb')])]:
  with pytest.raises(LLMError):render_mixed(choose(c,[]),ev,DocumentEvidence(service.facts),service.planner.plan(QUESTIONS['H06']),service.catalog,Trace('failure','q'),search_performed=searched,tool_failures=failures)

def test_oversized_real_price_evidence_refuses(tmp_path):
 import sqlite3
 s=independent_service(tmp_path)
 (s.settings.kb_dir/'KB-982.md').write_text('---\ntitle: 牛肉poke调价通知\neffective_from: 2026-06-01\n---\n牛肉poke售价调整为45元。')
 con=sqlite3.connect(s.settings.source_db)
 con.executemany('INSERT INTO sales VALUES (?,?,?,?,?,?,?)',[(f'PRICE{i}','2026-08-31','S02','P06','1',str(i+10),'现金') for i in range(100)]);con.commit();con.close()
 s.tools.close();s.rebuild()
 c={**CASES['H04'],'doc':'KB-982','needle':'调整为','query':'牛肉poke售价调价'}
 with pytest.raises(LLMError,match='证据超过'):run(s,QUESTIONS['H04'],c)

def test_notice_conflict_does_not_replace_actual(tmp_path):
 s=independent_service(tmp_path)
 (s.settings.kb_dir/'KB-982.md').write_text('---\ntitle: 牛肉poke调价通知\neffective_from: 2026-06-01\n---\n牛肉poke售价调整为47元。')
 s.rebuild();c={**CASES['H04'],'doc':'KB-982','needle':'调整为','query':'牛肉poke售价调价'}
 a,t=run(s,QUESTIONS['H04'],c)
 assert '不一致' in a.answer
 assert a.data_evidence[0]['result']['latest_price']==30
 assert a.data_evidence[0]['calculations'][0]['notice']['value']==47
 assert a.data_evidence[0]['calculations'][0]['result']==5
