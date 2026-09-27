import copy,json,sys
from pathlib import Path
from dataclasses import replace
import pytest
from test_replay import service,prepared,ROOT
from kbqa.mixed_answer import render_mixed
from kbqa.trace import Trace
from kbqa.llm import LLMError

# Guard the already-correct strict path; permissiveness only applies to a
# document-reason question with no precise user data scope or metric.
@pytest.mark.parametrize('variant',['reverse','outside-month','wrong-store','wrong-product','wrong-explicit-metric','precise-date','trend','unrelated-reason'])
def test_supplementary_scope_not_an_escape_hatch(service,variant):
 plan,ev,pool,p=prepared(service,'T02-1');ev=copy.deepcopy(ev);p=copy.deepcopy(p)
 selected=next(e for e in ev if e['_call_id']==p['results'][0]['call_id'])
 if variant=='reverse':
  selected['params']['start_a'],selected['params']['start_b']=selected['params']['start_b'],selected['params']['start_a']
  selected['params']['end_a'],selected['params']['end_b']=selected['params']['end_b'],selected['params']['end_a']
 elif variant=='outside-month':selected['params'].update(start_b='2026-08-06',end_b='2026-08-12')
 elif variant=='wrong-store':selected['params']['store_id']='S02'
 elif variant=='wrong-product':selected['params']['product_id']='P06'
 elif variant=='wrong-explicit-metric':plan.slots['metric_explicit']=True
 elif variant=='precise-date':
  plan.standalone='三文鱼poke 7月1日到7月31日为什么停售？'
 elif variant=='trend':plan.slots['context_effective']={'start':'2026-07-01','end':'2026-07-31','metric':'net_revenue'}
 else:p['facts']=[]
 with pytest.raises(LLMError):render_mixed(p,ev,pool,plan,service.catalog,Trace('negative','q'),search_performed=True)

def test_wrong_direction_recomputed_actual_results_still_rejected(service):
 plan,ev,pool,p=prepared(service,'C07');selected=next(e for e in ev if e['_call_id']==p['results'][0]['call_id'])
 wrong={**selected['params'],'start_a':'2026-08-01','end_a':'2026-08-31','start_b':'2026-07-01','end_b':'2026-07-31'}
 selected['params']=wrong;selected['result']=service.run_tool('compare_periods',wrong)
 with pytest.raises(LLMError):render_mixed(p,ev,pool,plan,service.catalog,Trace('reverse-real','q'),search_performed=True)

def test_local_subject_header_is_public_evidence(service):
 plan,ev,pool,p=prepared(service,'C07');a=render_mixed(p,ev,pool,plan,service.catalog,Trace('header','q'),search_performed=True)
 assert '吞拿鱼三明治的去留' in a.answer
 assert any('吞拿鱼三明治的去留' in c['quote'] for c in a.citations)
 assert '35%' in a.answer and '补充数据对照' in a.answer
 assert '不建议这么做' not in a.answer

def test_missing_by_store_does_not_claim_uniform_scoped_price(service):
 plan,ev,pool,p=prepared(service,'T03-2');e=next(x for x in ev if x['_call_id']==p['results'][0]['call_id'])
 e['result']={**e['result'],'by_store':{},'observed_unit_prices':{'42.00':6},'latest_price':42.0}
 a=render_mixed(p,ev,pool,plan,service.catalog,Trace('no-groups','q'),search_performed=True)
 assert '适用门店：S02' in a.answer and '不能逐店确认' in a.answer
 assert 'S02 实收单价 29.00' not in a.answer and '，与通知一致。' not in a.answer

@pytest.mark.parametrize('store,first_price,second_price',[('S01','31.25','49.50'),('S04','17.75','22.20')])
def test_scoped_prices_are_driven_by_independent_replacement_db(tmp_path,store,first_price,second_price):
 import sqlite3,shutil
 from kbqa.service import Service
 from kbqa.config import load_settings
 from kbqa.document_evidence import DocumentEvidence
 data=tmp_path/'data';data.mkdir();shutil.copy(ROOT/'data/pos.db',data/'pos.db')
 c=sqlite3.connect(data/'pos.db');c.execute('DELETE FROM sales')
 c.executemany('INSERT INTO sales VALUES(?,?,?,?,?,?,?)',[
 ('ONE','2026-06-18',store,'P06','1',first_price,'现金'),
 ('TWO','2026-06-18','S05','P06','1',second_price,'银行卡')]);c.commit();c.close()
 kb=tmp_path/'kb';kb.mkdir()
 (kb/'KB-981.md').write_text(f'---\ntitle: 牛肉poke活动通知\neffective_from: 2026-06-18\nstores: [{store}]\n---\n牛肉poke活动价{first_price}元，仅限当天。')
 (kb/'KB-982.md').write_text('---\ntitle: 商品数据说明\neffective_from: 2026-05-01\n---\nproducts表的unit_price是建档价，不能代替成交价。')
 s=Service(replace(load_settings(),data_dir=data,kb_dir=kb,var_dir=tmp_path/'var',llm_api_key='',llm_model='',llm_base_url=''))
 plan=s.planner.plan('6月18日牛肉poke多少钱一份，建档价能直接用吗？')
 params=dict(product_id='P06',start='2026-06-18',end='2026-06-18');result=s.run_tool('unit_price_check',params)
 pool=DocumentEvidence(s.facts);pool.add(s.run_tool('search_kb',dict(query='牛肉poke活动价建档价'),plan=plan)['evidence'])
 price=next(x for x in pool.items.values() if x['doc_id']=='KB-981' and '活动价' in x['quote'])
 policy=next(x for x in pool.items.values() if x['doc_id']=='KB-982' and '建档价' in x['quote'])
 p=dict(answer_type='hybrid',mode='price',results=[dict(call_id='db',metric='unit_price')],facts=[dict(evidence_id=price['evidence_id'],role='price'),dict(evidence_id=policy['evidence_id'],role='price_policy')])
 a=render_mixed(p,[dict(_call_id='db',tool='unit_price_check',params=params,result=result)],pool,plan,s.catalog,Trace('replacement','q'),search_performed=True)
 assert f'适用门店：{store}' in a.answer
 assert f'{store} 实收单价 {first_price}' in a.answer and f'S05 实收单价 {second_price}' in a.answer
 assert 'S02 实收' not in a.answer
 assert a.data_evidence[0]['calculations'][0]['notice']['stores']==[store]

def test_notice_cannot_leak_to_wrong_explicit_store(service):
 plan,ev,pool,p=prepared(service,'T03-2');plan.store_id='S03'
 selected=next(e for e in ev if e['_call_id']==p['results'][0]['call_id'])
 selected['params']={**selected['params'],'store_id':'S03'};selected['result']=service.run_tool('unit_price_check',selected['params'])
 assert selected['result']['latest_price']==42
 with pytest.raises(LLMError):render_mixed(p,ev,pool,plan,service.catalog,Trace('wrong-store','q'),search_performed=True)

def test_current_question_cannot_use_expired_one_day_activity(service):
 plan,ev,pool,p=prepared(service,'H04')
 r=service.run_tool('search_kb',dict(query='牛肉poke活动价仅限当天',top_k=10),plan=plan);pool.add(r['evidence'])
 activity=next(e for e in pool.items.values() if e['doc_id']=='KB-023' and '活动价' in e['quote'])
 p['facts'][0]['evidence_id']=activity['evidence_id']
 with pytest.raises(LLMError,match='当日'):render_mixed(p,ev,pool,plan,service.catalog,Trace('expired-activity','q'),search_performed=True)

@pytest.mark.parametrize('before,after',[(11,6),(6,17)])
def test_independent_event_reason_does_not_force_declining_data(tmp_path,before,after):
 import sqlite3,shutil
 from kbqa.service import Service
 from kbqa.config import load_settings
 from kbqa.document_evidence import DocumentEvidence
 data=tmp_path/'data';data.mkdir();shutil.copy(ROOT/'data/pos.db',data/'pos.db')
 c=sqlite3.connect(data/'pos.db');c.execute('DELETE FROM sales')
 c.executemany('INSERT INTO sales VALUES(?,?,?,?,?,?,?)',[
 ('A','2026-08-05','S01','P05',str(before),str(before*10),'现金'),
 ('B','2026-08-12','S01','P05',str(after),str(after*10),'现金'),
 ('LO','2026-05-01','S05','P01','1','1','现金'),('HI','2026-08-31','S05','P01','1','1','现金')]);c.commit();c.close()
 kb=tmp_path/'kb';kb.mkdir();(kb/'KB-981.md').write_text('---\ntitle: 鸡肉poke供应说明\neffective_from: 2026-08-11\nstores: [S01]\n---\n鸡肉poke的原料补给暂缓，供应履约需要重新排期。')
 s=Service(replace(load_settings(),data_dir=data,kb_dir=kb,var_dir=tmp_path/'var',llm_api_key='',llm_model='',llm_base_url=''))
 plan=s.planner.plan('S01鸡肉poke八月为什么暂停出售？')
 params=dict(start_a='2026-08-04',end_a='2026-08-10',start_b='2026-08-11',end_b='2026-08-17',store_id='S01',product_id='P05')
 result=s.run_tool('compare_periods',params);assert result['period_a']['qty']==before and result['period_b']['qty']==after
 pool=DocumentEvidence(s.facts);pool.add(s.run_tool('search_kb',dict(query='鸡肉poke供应原料补给'),plan=plan)['evidence'])
 doc=next(e for e in pool.items.values() if '补给暂缓' in e['quote'])
 p=dict(answer_type='hybrid',mode='anomaly',results=[dict(call_id='db',metric='qty')],facts=[dict(evidence_id=doc['evidence_id'],role='reason')])
 a=render_mixed(p,[dict(_call_id='db',tool='compare_periods',params=params,result=result)],pool,plan,s.catalog,Trace('event-replacement','q'),search_performed=True)
 assert a.answer_type=='hybrid' and '补给暂缓' in a.answer and '补充数据对照' in a.answer
 assert a.data_evidence[0]['calculations'][0]['result']['delta']==after-before
 assert ('涨了' if after>before else '跌了') in a.answer
 assert '未据此估算' in a.answer
