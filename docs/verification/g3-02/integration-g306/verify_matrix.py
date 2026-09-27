"""Network integration matrix, controller-only model and independent read-only SQL."""
import json,sqlite3,urllib.request,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).parent
OUT=Path(os.environ.get('G302_INTEGRATION_OUT',str(HERE)));OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'network-matrix.json').exists(), 'Use a fresh G302_INTEGRATION_OUT; never overwrite evidence'
resource=json.loads(Path(os.environ.get('G302_SERVER_RESOURCES',str(HERE/'server-resources.json'))).read_text());base=resource['base'];model=resource['model']
REF={'type':'daily_trend','start':'2026-06-01','end':'2026-06-30','store_id':'S02','metric':'net_revenue'}
def request(base,path='',body=None):
 r=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(r,timeout=180) as response:return json.load(response)
records=[]
conn=sqlite3.connect('file:'+resource['work']+'/var/clean.db?mode=ro',uri=True)
def net(start,end,store=None,product=None):
 clauses=['date BETWEEN ? AND ?'];params=[start,end]
 for field,value in [('store_id',store),('product_id',product)]:
  if value is not None:clauses.append(field+'=?');params.append(value)
 return conn.execute('SELECT COALESCE(SUM(amount_cents),0)/100.0 FROM sales_clean WHERE '+' AND '.join(clauses),params).fetchone()[0]

def run(name,q,case,expected='data',context=REF,no_model=False):
 request(model,'/case',case);before=request(model)['requests']
 payload={'question':q,'session_id':name}
 if context is not None:payload['context']=context
 a=request(base,'/api/chat',payload);t=request(base,'/api/trace/'+a['trace_id']);after=request(model)['requests']
 record={'name':name,'request':payload,'response':a,'trace':t,'model_calls':after-before};records.append(record)
 assert a['answer_type']==expected,record
 if no_model:assert after==before and not a['data_evidence']
 if expected=='data':
  e=a['data_evidence'][0];assert e['params']==case['params'],e
  assert after-before==2 and not t['errors']
  params=e['params'];result=e['result']
  if e['tool']=='compare_periods':
   for suffix,period in [('a','period_a'),('b','period_b')]:
    actual=net(params['start_'+suffix],params['end_'+suffix],params.get('store_id'),params.get('product_id'))
    assert result[period]['net_revenue']==actual
  else:assert result['net_revenue']==net(params['start'],params['end'],params.get('store_id'),params.get('product_id'))
 else:assert not a['data_evidence']
 return a,t

june={'start':'2026-06-01','end':'2026-06-30','store_id':'S02'}
run('ordinary-live-early-exit','预测模型训练前，请查询S02六月牛肉poke净营业额。',{'params':{**june,'product_id':'P06'}},context=None)
run('reference-original','这段时间净营业额是多少？',{'params':june})
run('reference-override','7月 S01 的净营业额是多少？',{'params':{'start':'2026-07-01','end':'2026-07-31','store_id':'S01'}})
run('unknown-store','预测模型训练前，请查询S99六月净营业额。',{},'refusal',no_model=True)
run('unknown-product','预测模型训练前，请查询S02 P99六月净营业额。',{},'refusal',no_model=True)
run('outside-period','预测模型训练前，请查询S02现在净营业额。',{},'refusal',no_model=True)
period=request(base,'/api/health')['data_period']
run('whole-period','预测模型训练前，请查询S02全部时间净营业额。',{'params':{'start':period['start'],'end':period['end'],'store_id':'S02'}})
comparison={'start_a':'2026-06-01','end_a':'2026-06-30','start_b':'2026-07-01','end_b':'2026-07-31','store_id':'S02'}
run('compare','预测模型训练前，请比较S02六月和七月净营业额。',{'tool':'compare_periods','params':comparison})
run('explicit-product','预测模型训练前，请比较S02 P06六月和七月净营业额。',{'tool':'compare_periods','params':{**comparison,'product_id':'P06'}})
run('comparison-unspecified','预测模型训练前，请查询S02六月和七月净营业额。',{},'clarify',no_model=True)
a,t=run('forbidden-added-product','这段时间净营业额是多少？',{'params':{**june,'product_id':'P06'}},'refusal')
assert any('error' in s['detail'].get('result',{}) for s in t['steps'] if s['step']=='tool')
run('forbidden-changed-product','预测模型训练前，请比较S02 P06六月和七月净营业额。',{'tool':'compare_periods','params':{**comparison,'product_id':'P07'}},'refusal')
a,t=run('forbidden-result-metric','这段时间净营业额是多少？',{'params':june,'metric':'orders'},'refusal')
assert any('趋势引用的最终指标' in e['message'] for e in t['errors'])
run('all-stores','全部门店这段时间净营业额是多少？',{'params':{'start':'2026-06-01','end':'2026-06-30'}})
run('document-with-reference','外卖订单多久内可以申请退款？',{'mode':'doc'},'doc')
a,t=run('safe-clarification-with-reference','外卖退款需要身份证吗？',{'no_tools':True,'content':json.dumps({'answer_type':'clarify','answer':'外卖退款不需要顾客出示身份证。请问还需要核对什么？'})},'clarify')
assert '身份证' not in a['answer'] and not t['errors']
conn.close()
(OUT/'network-matrix.json').write_text(json.dumps({'commit':resource['commit'],'execution':'controlled local HTTP only; SQL expected values independent of business tool','records':records},ensure_ascii=False,indent=2))
print(f'{len(records)} network cases passed; controlled model only; no paid calls')
