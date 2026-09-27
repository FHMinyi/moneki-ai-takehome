"""Actual HTTP: exact date is bound, unresolved entities are not explicit all."""
import json,os,sys
from pathlib import Path
import httpx,pytest
from integration_controller import ROOT,Model,runtime
sys.path.insert(0,str(ROOT/'docs/verification/g3-03'))
from test_mixed import CASES,QUESTIONS
OUT=Path(os.environ.get('G303_DAY_FOLLOWUP_OUT','/tmp/g303-day-followup'));OUT.mkdir(parents=True,exist_ok=True)
Model.cases[QUESTIONS['H02']]=dict(CASES['H02'])
@pytest.fixture(scope='module')
def server(tmp_path_factory):
 with runtime(tmp_path_factory.mktemp('day-followup-http'),handler=Model) as r:yield r

def ask(server,sid,q,params=None,context=None):
 if params is not None:Model.cases[q]=dict(mode='data',tool='query_metrics',params=params,metric='qty')
 body=dict(session_id=sid,question=q)
 if context is not None:body['context']=context
 with httpx.Client(trust_env=False,timeout=180) as c:
  a=c.post(server[0]+'/api/chat',json=body).json();t=c.get(server[0]+'/api/trace/'+a['trace_id']).json()
 (OUT/(sid+'-'+a['trace_id']+'.json')).write_text(json.dumps(dict(request=body,response=a,trace=t),ensure_ascii=False,indent=2)+'\n')
 return a,t

def step(t,name):return next(s['detail'] for s in t['steps'] if s['step']==name)

@pytest.mark.parametrize('wrong_day',[False,True])
def test_unknown_entities_keep_date_constraint(server,wrong_day):
 sid='unknown-'+str(wrong_day);a,_=ask(server,sid,QUESTIONS['H02']);assert a['answer_type']=='hybrid'
 p=dict(start='2026-06-18' if wrong_day else '2026-06-19',end='2026-06-18' if wrong_day else '2026-06-19',store_id='S02',product_id='P06')
 a,t=ask(server,sid,'那6月19日销量呢？',p)
 scope=step(t,'explicit_data_scope');assert scope['start']==scope['end']=='2026-06-19'
 assert scope['bound_entities']==[] and 'store_id' not in scope and 'product_id' not in scope
 if wrong_day:assert a['answer_type']=='refusal' and not a['data_evidence']
 else:assert a['answer_type']=='data' and a['data_evidence'][0]['params']==p

@pytest.mark.parametrize('wrong_entities',[False,True])
def test_current_explicit_entities_override_old_context(server,wrong_entities):
 sid='explicit-'+str(wrong_entities);a,_=ask(server,sid,QUESTIONS['H02']);assert a['answer_type']=='hybrid'
 p=dict(start='2026-06-19',end='2026-06-19',store_id='S02' if wrong_entities else 'S01',product_id='P06' if wrong_entities else 'P05')
 a,t=ask(server,sid,'那6月19日S01鸡肉poke销量呢？',p)
 scope=step(t,'explicit_data_scope');assert scope['store_id']=='S01' and scope['product_id']=='P05'
 assert set(scope['bound_entities'])=={'store_id','product_id'}
 assert a['answer_type']==('refusal' if wrong_entities else 'data')
 if not wrong_entities:assert a['data_evidence'][0]['params']==p
 else:assert not a['data_evidence'] and not a['citations']

@pytest.mark.parametrize('wrong_entities',[False,True])
def test_explicit_all_is_bound_not_unknown(server,wrong_entities):
 sid='all-'+str(wrong_entities);a,_=ask(server,sid,QUESTIONS['H02']);assert a['answer_type']=='hybrid'
 p=dict(start='2026-06-19',end='2026-06-19')
 if wrong_entities:p.update(store_id='S02',product_id='P06')
 a,t=ask(server,sid,'那6月19日全部门店所有商品销量呢？',p)
 scope=step(t,'explicit_data_scope');assert set(scope['bound_entities'])=={'store_id','product_id'}
 assert scope['store_id'] is None and scope['product_id'] is None
 assert a['answer_type']==('refusal' if wrong_entities else 'data')
 if not wrong_entities:
  assert a['data_evidence'][0]['params']==p
  assert a['data_evidence'][0]['result']['store_id'] is None and a['data_evidence'][0]['result']['product_id'] is None
 else:assert not a['data_evidence'] and not a['citations']

@pytest.mark.parametrize('extra_product',[False,True])
def test_trend_none_remains_explicit_all_product(server,extra_product):
 sid='trend-'+str(extra_product);a,_=ask(server,sid,QUESTIONS['H02']);assert a['answer_type']=='hybrid'
 p=dict(start='2026-06-19',end='2026-06-19',store_id='S03')
 if extra_product:p['product_id']='P06'
 context=dict(type='daily_trend',start='2026-06-19',end='2026-06-19',store_id='S03',metric='net_revenue')
 a,t=ask(server,sid,'6月19日销量是多少？',p,context)
 assert not any(s['step']=='explicit_data_scope' for s in t['steps'])
 effective=step(t,'context_resolution')['effective'];assert effective['store_id']=='S03' and effective.get('product_id') is None
 assert a['answer_type']==('refusal' if extra_product else 'data')
 if not extra_product:assert a['data_evidence'][0]['params']==p
 else:assert not a['data_evidence'] and not a['citations']
