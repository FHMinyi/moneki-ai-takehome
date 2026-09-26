"""G2-04 rebuilt real HTTP checks; no fixed retrieval or paid model."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import pytest

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('g203', ROOT/'docs/verification/g2-03/test_retrieval.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

@pytest.fixture
def rt(tmp_path,request):
    runtime=m.Runtime(tmp_path,request.node.name)
    yield runtime
    if os.environ.get('G2_EVIDENCE'):
        out=Path(os.environ['G2_EVIDENCE']);out.mkdir(parents=True,exist_ok=True)
        (out/(request.node.name+'.json')).write_text(json.dumps(dict(source=str(runtime.source),records=runtime.records),ensure_ascii=False,indent=2))

def original(rt):
    return m.original(rt)

def chat(request,q):
    a=request('/api/chat',dict(question=q,session_id='single'))
    t=request('/api/trace/'+a['trace_id'])
    return a,t

def detail(t,name):
    return next(s['detail'] for s in t['steps'] if s['step']==name)

def quotes(a,payload):
    assert len(a['citations'])<=4
    for c in a['citations']:
        norm=lambda s:re.sub(r'\s+','',s)
        assert 0<len(norm(c['quote']))<=400
        assert norm(c['quote']) in norm(payload['texts'][c['doc_id']])

PUBLIC=[json.loads(l) for l in (ROOT/'eval/public_questions.jsonl').read_text().splitlines() if json.loads(l)['category']=='doc' or json.loads(l)['id'] in ('V01','V02','S01')]

@pytest.mark.parametrize('q',PUBLIC,ids=lambda q:q['id'])
def test_document_route(rt,q):
    original(rt)
    with rt.serve() as req:a,t=chat(req,q['turns'][0]['question'])
    p=detail(t,'plan')
    assert p['intent']=='doc' and p['needs_docs'] and not p['needs_data'],p
    assert not a['data_evidence']

@pytest.mark.parametrize('q',PUBLIC,ids=lambda q:q['id'])
def test_document_facts(rt,q):
    payload=original(rt)
    with rt.serve() as req:a,t=chat(req,q['turns'][0]['question'])
    checks=q['turns'][0]['checks']; ids={c['doc_id'] for c in a['citations']}
    assert a['answer_type']=='doc',a
    assert set(checks.get('cite_all',[]))<=ids,a
    assert not set(checks.get('cite_none',[]))&ids,a
    quotes(a,payload)
    for mode in ('fact_all','fact_any'):
        f=checks.get(mode)
        if not f:continue
        body=' '.join(c['quote'] for c in a['citations'] if c['doc_id'] in f['docs'])+' '+a['answer']
        tests=[s in body for s in f['texts']]+[str(n['value']) in body.replace(',','') for n in f['numbers']]
        assert (all(tests) if mode=='fact_all' else any(tests)),a
    for n in checks.get('numbers_none',[]):
        assert not re.search(r'(?<!\d)'+str(n['value'])+r'(?!\d)',a['answer'].replace(',','')),a
    assert len(a['answer'])<1600,a
    assert detail(t,'evidence')['selected']

@pytest.mark.parametrize('question', ['外卖退款需要缴纳多少元手续费？','员工迟到申诉需要几天办结？','牛肉poke的花生含量是多少克？'])
def test_near_topic_missing(rt,question):
    payload=original(rt)
    with rt.serve() as req:a,t=chat(req,question)
    assert a['answer_type']=='refusal' and not a['citations'],a
    assert '没有' in a['answer'] or '不足' in a['answer']

@pytest.mark.parametrize('phase',['plan','evidence'])
def test_error_trace(rt,phase):
    original(rt)
    # Fault injection is limited to exception diagnostics, never RAG acceptance.
    target='self.planner.plan(question)' if phase=='plan' else 'self._document_evidence(plan, result, trace)'
    file=rt.source/'kbqa'/('service.py' if phase=='plan' else 'answerer.py')
    assert target in file.read_text()
    s=file.read_text().replace(target,"(_ for _ in ()).throw(RuntimeError('g204 injected failure'))")
    file.write_text(s)
    with rt.serve() as req:a,t=chat(req,'外卖退款政策是什么？')
    assert a['answer_type']=='refusal' and not a['citations'],a
    assert t['errors'] and t['errors'][0]['type']=='RuntimeError',t
    assert 'g204 injected failure' in t['errors'][0]['message']
