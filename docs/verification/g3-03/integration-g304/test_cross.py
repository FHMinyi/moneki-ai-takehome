import json,os,sys,time,sqlite3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import httpx,pytest
sys.path.insert(0,str(Path(__file__).parent))
from controller import Model,runtime,CASES,QUESTIONS
OUT=Path(os.environ.get('G303_CROSS_OUT','/tmp/g303-cross'));OUT.mkdir(parents=True,exist_ok=True)
@pytest.fixture(scope='module')
def server(tmp_path_factory):
 with runtime(tmp_path_factory.mktemp('g303-cross'),handler=Model) as r:yield r

def ask(server,sid,q,case=None,context=None):
 if case:Model.cases[q]=case
 base,resources=server
 with httpx.Client(trust_env=False,timeout=180) as c:
  req=dict(session_id=sid,question=q)
  if context is not None:req['context']=context
  started=time.monotonic();response=c.post(base+'/api/chat',json=req);elapsed=time.monotonic()-started
  assert response.status_code==200
  a=response.json();t=c.get(base+'/api/trace/'+a['trace_id']).json()
  (OUT/(sid+'-'+a['trace_id']+'.json')).write_text(json.dumps(dict(request=req,response=a,trace=t,elapsed=elapsed,resources=resources),ensure_ascii=False,indent=2))
 return a,t,elapsed

def step(t,name):return next(s['detail'] for s in t['steps'] if s['step']==name)
def model_prompt(t):return json.dumps(t['llm_calls'][0]['request']['messages'],ensure_ascii=False)
def data(tool,params,metric):return dict(mode='data',tool=tool,params=params,metric=metric)
def oracle(server,params):
 conn=sqlite3.connect('file:'+server[1]['var']+'/clean.db?mode=ro',uri=True)
 where='date BETWEEN ? AND ?';args=[params['start'],params['end']]
 for k in ['store_id','product_id']:
  if params.get(k):where+=' AND '+k+'=?';args.append(params[k])
 row=conn.execute('SELECT COALESCE(SUM(amount_cents),0)/100.0,COALESCE(SUM(CASE WHEN amount_cents>0 THEN qty WHEN amount_cents<0 THEN -qty ELSE 0 END),0),COUNT(DISTINCT CASE WHEN amount_cents>0 THEN order_id END) FROM sales_clean WHERE '+where,args).fetchone();conn.close();return row

def test_hybrid_then_changed_date_and_explicit_new_subject(server):
 a,t,_=ask(server,'changes',QUESTIONS['H02']);assert a['answer_type']=='hybrid'
 p=dict(start='2026-06-19',end='2026-06-19',store_id='S02',product_id='P06')
 b,u,_=ask(server,'changes','那6月19日销量呢？',data('query_metrics',p,'qty'))
 assert b['answer_type']=='data' and b['data_evidence'][0]['params']==p
 assert b['data_evidence'][0]['result']['qty']==oracle(server,p)[1]
 assert QUESTIONS['H02'] in model_prompt(u) and a['answer'] not in model_prompt(u)
 p=dict(start='2026-07-01',end='2026-07-31',store_id='S01',product_id='P05')
 c,v,_=ask(server,'changes','S01七月鸡肉poke订单数是多少？',data('query_metrics',p,'orders'))
 assert c['answer_type']=='data' and c['data_evidence'][0]['result']['orders']==oracle(server,p)[2]
 assert step(v,'plan')['store_id']=='S01' and step(v,'plan')['product_id']=='P05'

def test_natural_followup_receives_successful_mixed_question(server):
 a,t,_=ask(server,'natural',QUESTIONS['H01']);assert a['answer_type']=='hybrid'
 p=dict(start='2026-06-08',end='2026-06-14',store_id='S03')
 b,u,_=ask(server,'natural','能按天展开看看吗？',data('daily_metrics',p,'net_revenue'))
 assert b['answer_type']=='data' and b['data_evidence'][0]['params']==p
 assert QUESTIONS['H01'] in model_prompt(u) and a['answer'] not in model_prompt(u)
 assert sum(d['net_revenue'] for d in b['data_evidence'][0]['result']['days'])==oracle(server,p)[0]

def test_price_followup_retrieves_again_at_new_date(server):
 a,t,_=ask(server,'price',QUESTIONS['H04']);assert a['answer_type']=='hybrid'
 p=dict(product_id='P06',start='2026-07-01',end='2026-07-01')
 c={**CASES['H04'],'params':p,'query':'牛肉poke售价调整'}
 b,u,_=ask(server,'price','那7月1日呢？',c)
 assert b['answer_type']=='hybrid' and b['data_evidence'][0]['params']==p
 assert step(u,'session_context')['history_size']==1 and any(s['step']=='search' for s in u['steps'])
 assert all(x['scope']['as_of']=='2026-07-01' for x in b['citations'])
 assert set(x['evidence_id'] for x in a['citations']).isdisjoint(x['evidence_id'] for x in b['citations'])

def test_refusal_clears_mixed_context(server):
 a,_,_=ask(server,'failure',QUESTIONS['H02']);assert a['answer_type']=='hybrid'
 c={**CASES['H02'],'content':dict(answer_type='hybrid',mode='target',results=[dict(call_id='db',metric='net_revenue')],facts=[])}
 b,u,_=ask(server,'failure','请再次核对618当天S02牛肉poke销量是否达标？',c)
 assert b['answer_type']=='refusal' and not b['data_evidence'] and not b['citations']
 d,v,_=ask(server,'failure','那7月呢？')
 assert d['answer_type']=='clarify' and step(v,'session_context')['history_size']==0 and not v['llm_calls']

def test_clarify_independent_mixed_question_resets_prompt(server):
 a,t,_=ask(server,'clarify','8号的净营业额是多少？');assert a['answer_type']=='clarify'
 b,u,_=ask(server,'clarify',QUESTIONS['H04']);assert b['answer_type']=='hybrid'
 assert step(u,'model_context')['clarification_reset'] and '8号' not in model_prompt(u)

REF=dict(type='daily_trend',start='2026-06-08',end='2026-06-14',store_id='S03',metric='net_revenue')
@pytest.mark.parametrize('question',['这段时间营业额为什么异常？','那这段时间营业额为什么异常？','那这段时间呢？'])
def test_trend_mixed_replaces_previous_product(server,question):
 a,_,_=ask(server,'reference'+question,QUESTIONS['H02']);assert a['answer_type']=='hybrid'
 p=dict(start=REF['start'],end=REF['end'],store_id='S03')
 c={**CASES['H01'],'tool':'query_metrics','params':p,'query':QUESTIONS['H01']}
 b,u,_=ask(server,'reference'+question,question,c,REF)
 assert b['answer_type']=='hybrid',b
 assert b['data_evidence'][0]['params']==p and b['data_evidence'][0]['result']['net_revenue']==3630
 assert step(u,'plan')['product_id'] is None

def test_invalid_trend_refusal_clears_previous_context(server):
 a,_,_=ask(server,'invalid-ref',QUESTIONS['H02']);assert a['answer_type']=='hybrid'
 b,_,_=ask(server,'invalid-ref','这段时间呢？',context={**REF,'store_id':'S99'});assert b['answer_type']=='refusal'
 c,t,_=ask(server,'invalid-ref','那7月呢？')
 assert c['answer_type']=='clarify' and step(t,'session_context')['history_size']==0

def test_busy_mixed_is_bounded_and_does_not_erase_success(server):
 sid='busy';q='核对618当天S02牛肉poke销量和目标。';case={**CASES['H02'],'delay':1.1,'query':QUESTIONS['H02']};Model.entered.clear()
 with ThreadPoolExecutor(max_workers=2) as pool:
  first=pool.submit(ask,server,sid,q,case);assert Model.entered.wait(3)
  b,t,elapsed=ask(server,sid,'那7月呢？')
  assert b['answer_type']=='refusal' and '正在处理' in b['answer'] and elapsed<1
  assert step(t,'session_busy')['history_changed'] is False
  a,_,_=first.result();assert a['answer_type']=='hybrid'
 p=dict(start='2026-06-19',end='2026-06-19',store_id='S02',product_id='P06')
 c,u,_=ask(server,sid,'那6月19日销量呢？',data('query_metrics',p,'qty'))
 assert c['answer_type']=='data' and step(u,'session_context')['history_size']==1

def test_six_round_mixed_finalization_and_secrets(server):
 q='请核对618当天S02牛肉poke销量是否达标。';case={**CASES['H02'],'rounds':6,'query':QUESTIONS['H02']}
 a,t,_=ask(server,'six',q,case)
 assert a['answer_type']=='hybrid' and len(t['llm_calls'])==7
 assert t['llm_calls'][-1]['request']['tool_choice']=='none'
 assert 'controlled-not-a-secret' not in json.dumps(t,ensure_ascii=False)
 assert 'G303_G304_CONTROLLED_ONLY' not in json.dumps(a,ensure_ascii=False)
