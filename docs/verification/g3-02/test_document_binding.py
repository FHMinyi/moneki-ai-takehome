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
 ('2026年2月1日当时会员充值500元赠送多少？','KB-010','50'),
 ('Beef Poke里面有哪些过敏原？','KB-040','牛肉poke'),
])
def test_explicit_evidence_selection(service,question,doc,needle):
    answer,trace=run(service,question,lambda r:select(r,doc,needle),query='外卖退款政策' if doc=='KB-012' else None)
    assert answer.answer_type=='doc'
    assert needle in ''.join(c['quote'] for c in answer.citations)
    assert all(c['doc_id']==doc for c in answer.citations)
    assert any(s['step']=='document_binding' for s in trace.steps)

@pytest.mark.parametrize('question,doc,needle',[
 ('Beef Poke含花生吗？','KB-040','牛肉poke'),
 ('员工迟到申诉需要几天办结？','KB-016','15'),
 ('牛肉poke的花生含量是多少克？','KB-040','牛肉poke'),
 ('退款需要身份证吗？','KB-013','负金额'),
 ('外卖退款需要缴纳多少元手续费？','KB-013','200'),
 ('请核实员工餐能否享受免费配送？','KB-014','折'),
])
def test_real_nearby_span_not_sufficient(service,question,doc,needle):
    with pytest.raises(LLMError):run(service,question,lambda r:select(r,doc,needle))

@pytest.mark.parametrize('mutate',[
 lambda r: {'answer_type':'doc','facts':[{'evidence_id':'KB-013'}]},
 lambda r: {'answer_type':'doc','facts':[{'evidence_id':'doc-forged'}]},
 lambda r: {'answer_type':'doc','facts':[{'evidence_id':r['evidence'][0]['evidence_id'],'answer':'七天内退款'}]},
 lambda r: {'answer_type':'doc','facts':[{'evidence_id':r['evidence'][0]['evidence_id']}],'answer':'七天内退款'},
])
def test_no_forged_id_or_borrowed_claim(service,mutate):
    with pytest.raises(LLMError):run(service,'外卖退款时限是多少？',lambda r:json.dumps(mutate(r)))

PUBLIC_SELECTIONS={'C01':('KB-013','24'),'C02':('KB-040','牛肉poke'),'C03':('KB-062','23:00'),
 'C04':('KB-022','8,600'),'C05':('KB-061','发票在小程序'),'C06':('KB-001','净营业额**'),
 'C07':('KB-029','35%'),'C08':('KB-016','15'),'V01':('KB-023','29'),'V02':('KB-011','60'),
 'S01':('KB-060','12')}
QUESTIONS={q['id']:q['turns'][0]['question'] for q in map(json.loads,(ROOT/'eval/public_questions.jsonl').read_text().splitlines()) if q['id'] in PUBLIC_SELECTIONS}
@pytest.mark.parametrize('qid',PUBLIC_SELECTIONS)
def test_original_policy_cases_controlled(service,qid):
    doc,needle=PUBLIC_SELECTIONS[qid]
    answer,trace=run(service,QUESTIONS[qid],lambda r:select(r,doc,needle))
    assert answer.answer_type=='doc'
    assert any(c['doc_id']==doc and needle in c['quote'] for c in answer.citations)

def test_only_genuine_retrieval_can_create_evidence(service):
    from kbqa.document_evidence import DocumentEvidence
    from dataclasses import replace
    result=service.retriever.search('外卖退款',top_k=10)
    valid=result.ranked[0]
    for invalid in [replace(valid,padded=True),replace(valid,score=0),replace(valid,exclusion_reason='wrong version')]:
        modified=replace(result,hits=[invalid])
        assert not DocumentEvidence(service.facts,modified).public()
    pool=DocumentEvidence(service.facts,result)
    for item in pool.public():
        assert item['quote']==service.index.texts[item['doc_id']][item['source_start']:item['source_end']]
        assert item['chunk_id'] in {h.chunk_id for h in result.ranked}


def test_no_search_no_citation(service):
    from kbqa.document_evidence import DocumentEvidence
    pool=DocumentEvidence(service.facts)
    with pytest.raises(LLMError):
        pool.render(json.dumps({'answer_type':'doc','facts':[{'evidence_id':'KB-013'}]}),'外卖退款',Trace('empty','外卖退款'))

def test_model_receives_evidence_not_duplicate_diagnostics(service):
    client=Mock();seen=[]
    def respond(messages,*args,**kwargs):
        if not seen:
            seen.append(True)
            calls=[{'id':'search','type':'function','function':{'name':'search_kb','arguments':json.dumps({'query':'外卖退款时限是多少？','top_k':5})}}]
            return LLMReply({'role':'assistant','content':'','tool_calls':calls},'tool_calls','',calls,0)
        result=json.loads(messages[-1]['content'])['result']
        assert set(result)=={'evidence','scope'}
        content=select(result,'KB-013','24')
        return LLMReply({'role':'assistant','content':content},'stop',content,[],0)
    client.chat_with_retry.side_effect=respond
    trace=Trace('compact','外卖退款时限是多少？')
    answer=LiveEngine(client,service.answerer,service.run_tool,'2026-09-01',service.data_period).answer(service.planner.plan(trace.question),trace,[])
    assert answer.answer_type=='doc'
    assert any('diagnostics' in s['detail'].get('result',{}) for s in trace.steps if s['step']=='tool')

def test_scope_is_part_of_evidence_identity(service):
    from kbqa.document_evidence import DocumentEvidence
    from dataclasses import replace
    result=service.retriever.search('外卖退款')
    first=DocumentEvidence(service.facts,result)
    other=DocumentEvidence(service.facts,replace(result,scope={**result.scope,'store_id':'S03'}))
    assert set(first.items).isdisjoint(other.items)
    joint=DocumentEvidence(service.facts)
    assert len(joint.add(first.public()))==len(first.items)
    assert not joint.add(first.public())
    assert len(joint.add(other.public()))==len(other.items)
