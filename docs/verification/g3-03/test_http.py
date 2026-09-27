import json, os
from pathlib import Path
import httpx, pytest
from http_harness import runtime
from test_mixed import ROOT,CASES,QUESTIONS
OUT=Path(os.environ.get('G303_HTTP_OUT','/tmp/g303-http'));OUT.mkdir(parents=True,exist_ok=True)
@pytest.fixture(scope='module')
def server(tmp_path_factory):
 with runtime(tmp_path_factory.mktemp('g303-http')) as r:yield r
@pytest.mark.parametrize('qid',CASES)
def test_actual_http(server,qid):
 base,resources=server
 with httpx.Client(trust_env=False,timeout=180) as c:
  r=c.post(base+'/api/chat',json=dict(question=QUESTIONS[qid],session_id='g303-'+qid));assert r.status_code==200
  a=r.json();t=c.get(base+'/api/trace/'+a['trace_id']).json()
 (OUT/(qid+'.json')).write_text(json.dumps(dict(answer=a,trace=t,resources=resources),ensure_ascii=False,indent=2))
 assert a['answer_type']==('data' if qid=='H06' else 'hybrid'),a
 assert CASES[qid]['expected'] in a['answer']
 assert t['errors']==[]
 assert len(t['llm_calls'])==2
 assert 'G303_CONTROLLED' not in json.dumps(a)
 assert any(s['step']=='mixed_binding' for s in t['steps'])
 assert len(a['answer'])<=1200
 from kbqa.mixed_answer import compact
 assert all(len(compact(x['quote']))<=400 for x in a['citations'])

@pytest.mark.parametrize('label,expected',[('刷卡','银行卡按订单数占比 100.00%'),('银行卡','银行卡按订单数占比 100.00%'),('现金','现金按订单数占比 0.00%')])
def test_replacement_payment_classification_http(tmp_path,label,expected):
 import sqlite3
 from http_harness import Controlled
 from test_mixed import independent_service
 s=independent_service(tmp_path)
 con=sqlite3.connect(s.settings.source_db);con.execute("UPDATE sales SET payment='银行卡' WHERE amount='210.00'");con.commit();con.close();s.tools.close()
 q=f'6月18日S02{label}支付占比为什么异常？'
 Controlled.extra_cases[q]=dict(mode='payment',tool='payment_mix',params=dict(start='2026-06-18',end='2026-06-18',store_id='S02'),metric='share_orders',doc=None)
 try:
  with runtime(tmp_path/'http',data_dir=s.settings.data_dir,kb_dir=s.settings.kb_dir) as (base,resources):
   with httpx.Client(trust_env=False,timeout=180) as c:
    r=c.post(base+'/api/chat',json=dict(question=q,session_id='replacement'));assert r.status_code==200
    a=r.json();t=c.get(base+'/api/trace/'+a['trace_id']).json()
  (OUT/(f'payment-classification-{label}.json')).write_text(json.dumps(dict(question=q,response=a,trace=t),ensure_ascii=False,indent=2))
  assert a['answer_type']=='data' and expected in a['answer'] and not a['citations']
  assert '刷卡按订单数占比 0' not in a['answer']
  e=a['data_evidence'][0];assert e['result']['total_orders']==1
  assert e['result']['payments']['银行卡']['orders']==1 and e['result']['payments']['现金']['orders']==0
  assert all(x['denominator']==1 for x in e['calculations'])
 finally:Controlled.extra_cases.pop(q,None)
