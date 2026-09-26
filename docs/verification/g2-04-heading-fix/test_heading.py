"""Real rebuilt HTTP: structural headings cannot consume inferred-title prose."""
import importlib.util,json,os,subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('g204',ROOT/'docs/verification/g2-04/test_doc_qa.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@pytest.fixture
def rt(tmp_path,request):
    runtime=m.m.Runtime(tmp_path,request.node.name)
    yield runtime
    if os.environ.get('G2_EVIDENCE'):
        p=Path(os.environ['G2_EVIDENCE']);p.mkdir(parents=True,exist_ok=True)
        (p/(request.node.name+'.json')).write_text(json.dumps(dict(source=str(runtime.source),records=runtime.records),ensure_ascii=False,indent=2))

def aliases(rt):
    (rt.kb/'KB-970.md').write_text('| 标准写法 | alias |\n|---|---|\n| 翡翠饭 | Ivory Bowl |')

QUERIES=['翡翠饭的配送时限是多少分钟？','Ivory Bowl的配送时限是多少分钟？']

def check_spans(payload):
    for doc,meta in payload['docs'].items():
        for span in meta.get('heading_spans',[]):
            assert 0<=span['start']<span['end']<=len(payload['texts'][doc])
            assert span['text']==payload['texts'][doc][span['start']:span['end']]


def ask(req,payload,fact):
    check_spans(payload)
    for q in QUERIES:
        hits=req('/api/retrieve',dict(query=q,top_k=5))
        assert any(h['doc_id']=='KB-971' and fact in h['text'] and h['score']>0 and not h['padded'] for h in hits['results'])
        a,t=m.chat(req,q)
        assert a['answer_type']=='doc' and fact in a['answer'],a
        assert dict(doc_id='KB-971',quote=fact) in a['citations'],a
        m.quotes(a,payload,t)

@pytest.mark.parametrize('fmt',['md','utf8-txt','gbk-txt','html'])
def test_untitled_formats_and_fact_update(rt,fmt):
    aliases(rt)
    for number in (31,47):
        fact=f'翡翠饭的配送时限为{number}分钟。'
        suffix='txt' if fmt.endswith('txt') else fmt
        body=f'<html><body><p>{fact}</p></body></html>' if fmt=='html' else fact
        (rt.kb/('KB-971.'+suffix)).write_bytes(body.encode('gbk' if fmt=='gbk-txt' else 'utf-8'))
        payload=rt.build()
        with rt.serve() as req:ask(req,payload,fact)

@pytest.mark.parametrize('fmt',['md','html'])
@pytest.mark.parametrize('mode',['heading-only','heading-and-fact','same-text-twice','metadata-equals-body'])
def test_structural_heading_controls(rt,fmt,mode):
    aliases(rt);fact='翡翠饭的配送时限为31分钟。'
    if fmt=='md':
        body={'heading-only':'# '+fact,
              'heading-and-fact':'# 配送规范\n\n'+fact,
              'same-text-twice':'# '+fact+'\n\n'+fact,
              'metadata-equals-body':'---\ntitle: '+fact+'\n---\n'+fact}[mode]
    else:
        body={'heading-only':'<h1>'+fact+'</h1>',
              'heading-and-fact':'<h1>配送规范</h1><p>'+fact+'</p>',
              'same-text-twice':'<h1>'+fact+'</h1><p>'+fact+'</p>',
              'metadata-equals-body':'<head><title>'+fact+'</title></head><body><p>'+fact+'</p></body>'}[mode]
    (rt.kb/('KB-971.'+fmt)).write_text(body)
    payload=rt.build()
    check_spans(payload)
    with rt.serve() as req:
        if mode!='heading-only':ask(req,payload,fact)
        else:
            for q in QUERIES:
                a,t=m.chat(req,q)
                assert a['answer_type']=='refusal' and not a['citations'],a


def test_long_markdown_heading_does_not_merge_body(rt):
    aliases(rt);fact='翡翠饭的配送时限为31分钟。'
    (rt.kb/'KB-971.md').write_text('# 配送规范'+('补充条款'*10)+'\n\n'+fact)
    payload=rt.build()
    with rt.serve() as req:
        for q in QUERIES:
            a,t=m.chat(req,q)
            selected=m.detail(t,'evidence')['selected']
            assert any(x['doc_id']=='KB-971' and x['quote']==fact for x in selected),t
            chunks={c['chunk_id']:c for c in payload['chunks']}
            for picked in selected:
                chunk=chunks[picked['chunk_id']]
                assert picked['doc_id']==chunk['doc_id']=='KB-971'
                assert picked['source_start']==chunk['source_start'] and picked['source_end']==chunk['source_end']
                original=payload['texts']['KB-971'][chunk['source_start']:chunk['source_end']]
                assert original==chunk['source_text'] and picked['quote'] in original
            if a['answer_type']=='doc':
                m.quotes(a,payload,t)
            else:
                # The original long-title alias probe is conservatively refused
                # by an existing score gate. This test constrains prose identity,
                # not a newly invented no-model answer-rate requirement.
                assert a['answer_type']=='refusal' and not a['citations'],a


def test_literal_hash_in_plain_text_is_prose(rt):
    aliases(rt);fact='# 翡翠饭的配送时限为31分钟。'
    (rt.kb/'KB-971.txt').write_text(fact)
    payload=rt.build()
    with rt.serve() as req:ask(req,payload,fact)


def test_actual_old_cache_preserves_prose_and_heading_identity(rt):
    aliases(rt);fact='翡翠饭的配送时限为31分钟。'
    (rt.kb/'KB-971.html').write_text('<p>'+fact+'</p>')
    (rt.kb/'KB-972.html').write_text('<h1>夜班预约应提前19小时提交。</h1>')
    current={name:(rt.source/'kbqa'/name).read_bytes() for name in ('loader.py','units.py')}
    for name in current:
        (rt.source/'kbqa'/name).write_bytes(subprocess.check_output(['git','show','358859a:'+('starter/kbqa/'+name)],cwd=ROOT))
    old=rt.build()
    for name,data in current.items():(rt.source/'kbqa'/name).write_bytes(data)
    # No manual cache deletion/rebuild after restoring the implementation.
    with rt.serve() as req:
        payload=json.loads(rt.cache.read_text())
        ask(req,payload,fact)
        a,t=m.chat(req,'夜班预约应提前多少小时提交？')
        assert a['answer_type']=='refusal' and not a['citations'],a
    rt.records.append(dict(old_cache_key=old['key'],loaded_cache_key=payload['key']))

@pytest.mark.parametrize('shape',['md-sentences','md-windows','html-inline'])
def test_true_heading_sentences_and_windows(rt,shape):
    aliases(rt);fact='翡翠饭的配送时限为31分钟。'
    if shape=='html-inline':
        body='<html><body><h2>配送规范。<em>'+fact+'</em></h2></body></html>';suffix='html'
    else:
        body='# 配送规范'+('补充条款'*90 if shape=='md-windows' else '')+'。'+fact;suffix='md'
    (rt.kb/('KB-971.'+suffix)).write_text(body)
    rt.build()
    with rt.serve() as req:
        a,t=m.chat(req,QUERIES[0])
    assert a['answer_type']=='refusal' and not a['citations'],a
    assert not m.detail(t,'evidence')['candidates'],t

@pytest.mark.parametrize('q',['Unknown Dish的配送时限是多少分钟？','Ivory Bowl需要提供身份证吗？'],ids=['unknown-subject','known-subject-missing-fact'])
def test_long_heading_subject_guards(rt,q):
    aliases(rt)
    (rt.kb/'KB-971.md').write_text('# 配送规范'+('补充条款'*10)+'\n\n翡翠饭的配送时限为31分钟。')
    rt.build()
    with rt.serve() as req:a,t=m.chat(req,q)
    assert a['answer_type']=='refusal' and not a['citations'],a
