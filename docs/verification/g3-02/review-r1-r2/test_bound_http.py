"""Actual HTTP/rebuild with explicit controlled same-response bindings."""
import sys,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'docs/verification/g3-02'))
sys.path.insert(0,str(Path(__file__).parent))
from test_http import runtime,chat
from test_document_binding import PUBLIC_SELECTIONS,QUESTIONS
from test_anchored_selection import PUBLIC_BINDINGS,anchored,duration,TEXT

@pytest.mark.parametrize('qid',PUBLIC_BINDINGS)
def test_public_bound_http(tmp_path,qid):
 doc,needle=PUBLIC_SELECTIONS[qid]
 with runtime(tmp_path,{'selector':anchored(doc,needle,*PUBLIC_BINDINGS[qid])}) as (r,serve,payload):
  with serve() as request:a,t=chat(request,QUESTIONS[qid])
 assert a['answer_type']=='doc',a
 assert any(s['step']=='document_binding' for s in t['steps'])
 assert len(t['llm_calls'])==2  # no second model/verifier added
 for c in a['citations']:
  assert c['quote']==payload['texts'][c['doc_id']][c['source_start']:c['source_end']]

@pytest.mark.parametrize('q,doc,needle,subject,attribute,value',[
 ('外卖订单多久内可以退款？','KB-013','堂食订单须当场',('外卖订单','堂食订单'),('退款','退款'),TEXT),
 ('办理外卖退款应当出示什么身份证件？','KB-014','工牌',('外卖','员工'),('身份证件','工牌'),TEXT),
 ('员工迟到申诉多久能处理完？','KB-016','15',('迟到申诉','迟到'),('处理','记'),duration('多久','15 分钟')),
 ('外卖订单多久内可以退款？','KB-011','30',('外卖订单','储值本金'),('退款','退回'),duration('多久','30 天')),
 ('迟到申诉多久？','KB-016','15',('迟到','迟到'),('迟到','迟到'),duration('多久','15 分钟')),
])
def test_wrong_or_omitted_binding_http(tmp_path,q,doc,needle,subject,attribute,value):
 with runtime(tmp_path,{'selector':anchored(doc,needle,subject,attribute,value),'params':{'query':q,'top_k':10}}) as (r,serve,payload):
  with serve() as request:a,t=chat(request,q)
 assert a['answer_type']=='refusal' and not a['citations']
 assert any(s['step']=='document_binding_rejected' for s in t['steps'])
 assert any(s['step']=='insufficient_evidence' for s in t['steps'])

@pytest.mark.parametrize('fmt',['md','txt','gbk','html'])
def test_new_kb_rebuild_bound_http(tmp_path,fmt):
 suffix='txt' if fmt=='gbk' else fmt
 name='KB-985.'+suffix
 def material(n):
  text=f'霓虹订单退款须在{n}分钟内提出。'
  if fmt=='html':text='<h2>退款受理</h2><p>'+text+'</p>'
  return text.encode('gbk' if fmt=='gbk' else 'utf-8')
 case={'selector':anchored('KB-985','43',('霓虹订单','霓虹订单'),('退款','退款'),duration('多久','43分钟'))}
 with runtime(tmp_path,case,{name:material(43)}) as (r,serve,payload):
  with serve() as request:a,t=chat(request,'霓虹订单退款多久内提出？')
  assert a['answer_type']=='doc' and '43' in a['answer']
  (r.kb/name).write_bytes(material(89));r.build()
  case['selector']=anchored('KB-985','89',('霓虹订单','霓虹订单'),('退款','退款'),duration('多久','89分钟'))
  with serve() as request:b,u=chat(request,'霓虹订单退款多久内提出？')
  assert b['answer_type']=='doc' and '89' in b['answer'] and '43' not in b['answer']
  assert a['citations'][0]['evidence_id']!=b['citations'][0]['evidence_id']
