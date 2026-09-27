import sys,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'docs/verification/g3-02'))
sys.path.insert(0,str(ROOT/'docs/verification/g3-02/review-r1-r2'))
import test_http as h
from test_anchored_selection import anchored,duration

@pytest.mark.parametrize('attribute',[('多久','24 小时'),('退款','退款')])
def test_actual_http_arrival_not_window(tmp_path,attribute):
 q='外卖退款多久能到账？'
 case={'selector':anchored('KB-013','24',('退款','退款'),attribute,duration('多久','24 小时')),'params':{'query':q,'top_k':5}}
 with h.runtime(tmp_path,case) as (r,serve,payload):
  with serve() as req:a,t=h.chat(req,q)
 assert a['answer_type']=='refusal' and not a['citations']
 assert not t['errors'] and any(s['step']=='document_binding_rejected' for s in t['steps'])


def test_actual_http_functional_subject(tmp_path):
 q='外卖订单多久内可以退款？'
 with h.runtime(tmp_path,{'selector':anchored('KB-011','30',('内','内'),('多久','30 天'),duration('多久','30 天')),'params':{'query':q,'top_k':10}}) as (r,serve,payload):
  with serve() as req:a,t=h.chat(req,q)
 assert a['answer_type']=='refusal' and not a['citations']
 assert any('subject_is_not_a_business_subject' in str(s) for s in t['steps'])

@pytest.mark.parametrize('name,action,other',[('星砂订单','签收','复核'),('云帆工单','归档','分派')])
def test_actual_http_same_dimension_actions(tmp_path,name,action,other):
 kb={'KB-989.md':f'# {name}时限\n\n{name}{action}须在43分钟内完成。\n\n{name}{other}须在89分钟内完成。'}
 q=f'{name}多久能{action}？'
 case={'selector':anchored('KB-989','89',(name,name),('多久','89分钟'),duration('多久','89分钟'))}
 with h.runtime(tmp_path,case,kb) as (r,serve,payload):
  with serve() as req:
   bad,t=h.chat(req,q)
   # Now provide a non-scalar but uninformative attribute: the requested
   # post-focus action still cannot be dropped just by using the subject twice.
   case['selector']=anchored('KB-989','89',(name,name),(name,name),duration('多久','89分钟'))
   omitted,u=h.chat(req,q)
   case['selector']=anchored('KB-989','43',(name,name),(action,action),duration('多久','43分钟'))
   good,v=h.chat(req,q)
 assert bad['answer_type']==omitted['answer_type']=='refusal'
 assert good['answer_type']=='doc' and '43' in good['answer']
 assert any('post_focus_business_predicate_omitted' in str(s) for s in u['steps'])
 assert all(len(trace['llm_calls'])==2 for trace in (t,u,v))

@pytest.mark.parametrize('payload',[
 {'answer_type':'clarify','answer':'外卖退款不需要顾客出示身份证。请问还需要核对什么？'},
 {'answer_type':'clarify','answer':'门店退款收取手续费。请补充日期范围。'},
 {'answer_type':'clarify','missing_fields':['date_range','store']},
])
def test_actual_http_clarify_state_without_retrieval(tmp_path,monkeypatch,payload):
 def response(self):
  self.rfile.read(int(self.headers['Content-Length']))
  body=json.dumps({'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(payload)}}]}).encode()
  self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 monkeypatch.setattr(h.Controlled,'do_POST',response)
 with h.runtime(tmp_path,{'controlled_state_only':True}) as (r,serve,source):
  with serve() as req:a,t=h.chat(req,'外卖退款需要身份证吗？')
 assert a['answer_type']=='clarify' and not a['citations'] and not a['data_evidence'] and not t['errors']
 assert not any(s['step'] in ('search','tool') for s in t['steps'])
 assert all(w not in a['answer'] for w in ['身份证','手续费','退款'])
 assert any(s['step']=='clarification_state' for s in t['steps'])
 if 'missing_fields' in payload:assert a['answer']=='请补充日期范围和门店。'
