import importlib.util,json,os,sys
from pathlib import Path
import httpx,pytest
from integration_controller import ROOT,Model,runtime,QUESTIONS
OUT=Path(os.environ.get('G303_INTEGRATED_HTTP','/tmp/g303-integrated-http'));OUT.mkdir(parents=True,exist_ok=True)

def chat(base,sid,q):
 with httpx.Client(trust_env=False,timeout=180) as c:
  r=c.post(base+'/api/chat',json=dict(session_id=sid,question=q));assert r.status_code==200
  a=r.json();t=c.get(base+'/api/trace/'+a['trace_id']).json()
  (OUT/(sid+'-'+a['trace_id']+'.json')).write_text(json.dumps(dict(question=q,response=a,trace=t),ensure_ascii=False,indent=2)+'\n')
 return a,t

def test_mixed_then_minimal_doc_then_exact_data(server):
 base,_=server
 a,_=chat(base,'mixed-doc-data',QUESTIONS['H04']);assert a['answer_type']=='hybrid'
 q='外卖订单多久内可以退款？';Model.cases[q]=dict(mode='doc',doc='KB-013',needle='24',query=q)
 b,t=chat(base,'mixed-doc-data',q);assert b['answer_type']=='doc' and '24' in b['answer']
 payload=json.loads(t['llm_calls'][-1]['response']['choices'][0]['message']['content'])
 assert set(payload['facts'][0])=={'evidence_id'}
 assert all(x['request']['max_tokens']==8192 for x in t['llm_calls'])
 q='S02 6月18日牛肉poke销量是多少？';params=dict(start='2026-06-18',end='2026-06-18',store_id='S02',product_id='P06')
 Model.cases[q]=dict(mode='data',tool='query_metrics',params=params,metric='qty')
 c,u=chat(base,'mixed-doc-data',q);assert c['answer_type']=='data' and c['data_evidence'][0]['result']['qty']==125
 assert c['data_evidence'][0]['params']==params
 assert any(s['step']=='explicit_data_scope' for s in u['steps'])

@pytest.fixture(scope='module')
def server(tmp_path_factory):
 with runtime(tmp_path_factory.mktemp('merged-minimal-doc'),handler=Model) as r:yield r

@pytest.mark.parametrize('wrong_range',[('2026-06-18','2026-07-01'),('2026-07-01','2026-07-01'),('2026-09-01','2026-09-01')])
def test_exact_day_model_query_cannot_widen_or_exchange_scope(tmp_path,wrong_range):
 spec=importlib.util.spec_from_file_location('date_fixture',ROOT/'docs/verification/g3-04/date-scope-repair/replay_http.py')
 fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
 data,kb,rows=fixture.prepare(tmp_path)
 q='S02 6月18日红岩饭销量是多少？'
 with runtime(tmp_path/'server',data_dir=data,kb_dir=kb,handler=Model) as (base,_):
  Model.cases[q]=dict(mode='data',tool='query_metrics',params=dict(start='2026-06-18',end='2026-06-18',store_id='S02',product_id='P06'),metric='qty')
  good,t=chat(base,'replacement-good-'+'-'.join(wrong_range),q);assert good['answer_type']=='data' and good['data_evidence'][0]['result']['qty']==9-2
  Model.cases[q]=dict(mode='data',tool='query_metrics',params=dict(start=wrong_range[0],end=wrong_range[1],store_id='S02',product_id='P06'),metric='qty')
  bad,u=chat(base,'replacement-bad-'+'-'.join(wrong_range),q);assert bad['answer_type']=='refusal' and not bad['data_evidence'] and not bad['citations']
  tools=[s['detail'] for s in u['steps'] if s['step']=='tool'];assert tools and all('error' in s['result'] for s in tools)
  assert any(s['step']=='explicit_data_scope' and s['detail']['start']=='2026-06-18' for s in u['steps'])

@pytest.mark.parametrize('question,expected',[
 ('三文鱼poke 七月为什么停售了？','hybrid'),
 ('三文鱼poke 7月6日为什么停售了？','refusal'),
])
def test_document_reason_supplement_cannot_override_exact_day(server,question,expected):
 base,_=server
 Model.cases[question]=dict(mode='anomaly',tool='compare_periods',params=dict(start_a='2026-06-29',end_a='2026-07-05',start_b='2026-07-06',end_b='2026-07-12',product_id='P04'),metric='qty',doc='KB-021',needle='本批次三文鱼到货质检不合格',role='reason',query='三文鱼poke 七月初 停售')
 a,t=chat(base,'reason-'+expected,question)
 assert a['answer_type']==expected,a
 if expected=='hybrid':
  assert '补充数据对照' in a['answer'] and a['data_evidence'][0]['result']['period_b']['qty']==0
  assert '质检不合格' in a['answer']
 else:
  assert not a['data_evidence'] and not a['citations']
  assert any('查询日期或比较方向' in e['message'] for e in t['errors'])
