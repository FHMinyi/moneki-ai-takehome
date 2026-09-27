"""Reviewer regressions with actual retrieval; no paid calls."""
import json,sys
from pathlib import Path
from unittest.mock import Mock
from dataclasses import replace
import pytest
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'starter'))
from kbqa.config import load_settings
from kbqa.service import Service
from kbqa.live import LiveEngine
from kbqa.llm import LLMReply,LLMError
from kbqa.trace import Trace

@pytest.fixture(scope='module')
def service(tmp_path_factory):
 return Service(replace(load_settings(),var_dir=tmp_path_factory.mktemp('review-g302'),llm_api_key='',llm_base_url='',llm_model=''))

def execute(service,q,final,search=True):
 client=Mock();seen=[]
 def reply(messages,*a,**kw):
  if search and not seen:
   seen.append(True)
   tc=[{'id':'review-search','type':'function','function':{'name':'search_kb','arguments':json.dumps({'query':q,'top_k':10})}}]
   return LLMReply({'role':'assistant','content':'','tool_calls':tc},'tool_calls','',tc,0)
  result=json.loads(next(m['content'] for m in reversed(messages) if m['role']=='tool'))['result'] if search else {}
  text=final(result) if callable(final) else final
  return LLMReply({'role':'assistant','content':text},'stop',text,[],0)
 client.chat_with_retry.side_effect=reply
 trace=Trace('review',q)
 answer=LiveEngine(client,service.answerer,service.run_tool,'2026-09-01',service.data_period).answer(service.planner.plan(q),trace,[])
 return answer,trace

def pick(doc,needle):
 def choose(r):
  e=next(e for e in r['evidence'] if e['doc_id']==doc and needle in e['quote'])
  return json.dumps({'answer_type':'doc','facts':[{'evidence_id':e['evidence_id']}]})
 return choose

@pytest.mark.parametrize('q,doc,needle',[
 ('外卖订单多久内可以退款？','KB-013','堂食订单须当场'),
 ('办理外卖退款应当出示什么身份证件？','KB-014','工牌'),
 ('员工迟到申诉多久能处理完？','KB-016','15'),
 ('外卖订单多久内可以退款？','KB-011','30'),
])
def test_r1_open_subject_attribute(service,q,doc,needle):
 try:a,t=execute(service,q,pick(doc,needle))
 except LLMError:return
 assert a.answer_type=='refusal' and not a.citations,a

@pytest.mark.parametrize('text',[
 '外卖退款不需要顾客出示身份证。',
 '所有门店退货必须扣除手续费。',
 'v2（KB-013）表示退款不需要身份证。',
])
def test_r2_refusal_cannot_carry_policy_assertion_without_search(service,text):
 a,t=execute(service,'外卖退款需要身份证吗？',json.dumps({'answer_type':'refusal','answer':text}),search=False)
 assert a.answer_type=='refusal' and not a.citations
 assert text not in a.answer and '无法确定' in a.answer
 assert any(s['step']=='insufficient_evidence' for s in t.steps)


def test_r2_explicit_state_has_no_free_text(service):
 a,t=execute(service,'任意制度问题',json.dumps({'answer_type':'refusal','reason':'insufficient_evidence'}),search=False)
 assert a.answer_type=='refusal' and '无法确定' in a.answer and not a.citations


def test_r2_replay_saved_chat7_final(service):
 saved=json.loads((ROOT/'docs/verification/g3-02/live/chat-7.json').read_text())
 content=saved['trace']['llm_calls'][-1]['response']['choices'][0]['message']['content']
 a,t=execute(service,saved['question'],content)
 assert a.answer_type=='refusal' and '无法确定' in a.answer and 'v2' not in a.answer and 'KB-013' not in a.answer
 assert not a.citations and any(s['step']=='insufficient_evidence' for s in t.steps)
