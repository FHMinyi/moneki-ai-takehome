"""Controlled model inputs; genuine retrieval and service entry, never live-model evidence."""
import json, sys
from pathlib import Path
from dataclasses import replace
from unittest.mock import Mock
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'starter'))
from kbqa.config import load_settings
from kbqa.service import Service
from kbqa.live import LiveEngine
from kbqa.llm import LLMReply, LLMError
from kbqa.trace import Trace

@pytest.fixture(scope='module')
def service(tmp_path_factory):
    return Service(replace(load_settings(),var_dir=tmp_path_factory.mktemp('g302'),llm_api_key='',llm_base_url='',llm_model=''))

def run(service, question, final, query=None):
    client=Mock(); seen=[]
    def respond(messages,*args,**kwargs):
        if not seen:
            seen.append(True)
            calls=[{'id':'search-actual-1','type':'function','function':{'name':'search_kb','arguments':json.dumps({'query':query or question,'top_k':5})}}]
            return LLMReply({'role':'assistant','content':'','tool_calls':calls},'tool_calls','',calls,0)
        result=json.loads(messages[-1]['content'])['result']
        content=final(result) if callable(final) else final
        return LLMReply({'role':'assistant','content':content},'stop',content,[],0)
    client.chat_with_retry.side_effect=respond
    trace=Trace('controlled',question)
    engine=LiveEngine(client,service.answerer,service.run_tool,'2026-09-01',service.data_period)
    return engine.answer(service.planner.plan(question),trace,[]),trace

@pytest.mark.parametrize('question,content',[
 ('外卖订单多久内可以退款？','外卖订单可以在7天内退款。[KB-012]'),
 ('Beef Poke含花生吗？','Beef Poke含花生。[KB-040]'),
 ('员工餐免费吗？','员工餐免费。[KB-014]'),
 ('退款需要身份证吗？','退款需要身份证。[KB-013]'),
 ('外卖订单多久内可以退款？','外卖订单退款时限为48小时。[KB-013]'),
])
def test_unbound_claims_rejected(service,question,content):
    with pytest.raises(LLMError):run(service,question,content)

def select(result, doc, needle):
    candidates=[e for e in result.get('evidence',[]) if e['doc_id']==doc and needle in e['quote']]
    assert candidates, result
    return json.dumps({'answer_type':'doc','facts':[{'evidence_id':candidates[0]['evidence_id']}]})

@pytest.mark.parametrize('question,doc,needle',[
 ('外卖订单多久内可以退款？','KB-013','24'),
 ('2026年6月14日当时外卖订单多久内可以退款？','KB-012','7 天'),
 ('2025年12月1日当时会员充值500元赠送多少？','KB-010','50'),
 ('Beef Poke里面有哪些过敏原？','KB-040','Beef Poke'),
])
def test_explicit_evidence_selection(service,question,doc,needle):
    answer,trace=run(service,question,lambda r:select(r,doc,needle),query='外卖退款政策' if doc=='KB-012' else None)
    assert answer.answer_type=='doc'
    assert needle in ''.join(c['quote'] for c in answer.citations)
    assert all(c['doc_id']==doc for c in answer.citations)
    assert any(s['step']=='document_binding' for s in trace.steps)
