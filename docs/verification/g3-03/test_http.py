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

@pytest.mark.parametrize('cash,card,expected',[('9.99','0.50','9.99 / 10.49 元'),('9.99','-9.99','9.99 / 0.00 元'),('-9.99','20.48','-9.99 / 10.49 元')])
def test_fractional_money_operands_actual_http(tmp_path,cash,card,expected):
 import sqlite3
 from http_harness import Controlled
 from test_mixed import independent_service
 s=independent_service(tmp_path)
 con=sqlite3.connect(s.settings.source_db);con.execute("DELETE FROM sales WHERE store_id='S02'")
 con.executemany('INSERT INTO sales VALUES (?,?,?,?,?,?,?)',[
 ('CENTS-CASH','2026-06-18','S02','P06','1',cash,'现金'),('CENTS-CARD','2026-06-18','S02','P06','1',card,'银行卡')]);con.commit();con.close();s.tools.close()
 q='6月18日S02现金支付金额占比是多少，为什么？'
 Controlled.extra_cases[q]=dict(mode='payment',tool='payment_mix',params=dict(start='2026-06-18',end='2026-06-18',store_id='S02'),metric='share_revenue',doc=None)
 try:
  with runtime(tmp_path/'http',data_dir=s.settings.data_dir,kb_dir=s.settings.kb_dir) as (base,resources):
   with httpx.Client(trust_env=False,timeout=180) as c:
    r=c.post(base+'/api/chat',json=dict(question=q,session_id='cents'));assert r.status_code==200
    a=r.json();t=c.get(base+'/api/trace/'+a['trace_id']).json()
  (OUT/(f'fractional-payment-{cash}-{card}.json')).write_text(json.dumps(dict(question=q,response=a,trace=t),ensure_ascii=False,indent=2))
  assert a['answer_type']=='data' and expected in a['answer'],a
  from decimal import Decimal,ROUND_HALF_UP
  numerator=Decimal(cash);denom=Decimal(cash)+Decimal(card)
  calculated=a['data_evidence'][0]['calculations'][0]
  assert calculated['numerator']==float(numerator) and calculated['denominator']==float(denom)
  if denom:
   pct=(numerator*100/denom).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
   assert calculated['result']==float(pct) and f'{pct:.2f}%' in a['answer']
  else:assert calculated['result'] is None and '分母为零' in a['answer']
 finally:Controlled.extra_cases.pop(q,None)
