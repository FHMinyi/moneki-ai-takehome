"""Independent authored KB lifecycle expectations through public rebuild and real HTTP.
No product loader/index/answer function is used to derive expected facts or quotes.
Invoke using freshly installed source/starter/.venv/bin/python, --source exported tree.
"""
import argparse, hashlib, importlib.util, json, os, re, shutil, sys, unicodedata
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
source=a.source.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location('verified_runtime',source/'docs/verification/g2-03/test_retrieval.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rt=m.Runtime(out,'independent-kb-lifecycle');cases=[]
def norm(s):return re.sub(r'[\s*`|#>]','',unicodedata.normalize('NFKC',s))
def write(name,body,encoding='utf-8'):(Path(rt.env['KB_DIR'])/name).write_bytes(body.encode(encoding))
def save():
    (out/'http.json').write_text(json.dumps(dict(source=str(rt.source),records=rt.records,cases=cases),ensure_ascii=False,indent=2)+'\n')
def check_strict(name,expected,checks,stale=()):
    kb=Path(rt.env['KB_DIR'])
    snapshot=out/'input-snapshots'/name;snapshot.mkdir(parents=True)
    for f in kb.iterdir():
        if f.is_file():shutil.copyfile(f,snapshot/f.name)
    before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in kb.iterdir() if f.is_file()}
    rt.build()  # public python -m kbqa.rebuild
    result=dict(stage=name,expected=expected,input_sha256=before,checks=[],passed=False);cases.append(result)
    with rt.serve() as req:
        h=req('/api/health');assert h['kb_docs']==len(expected) and h['llm_mode']=='mock',h
        for question,gold,fact in checks:
            retrieval=req('/api/retrieve',dict(query=question,top_k=100))
            hits=retrieval['results']
            assert len(hits)==min(100,h['kb_chunks'])
            for hit in hits:
                assert hit['doc_id'] in expected
                assert norm(hit['text']) in norm(expected[hit['doc_id']]),hit
                for span in hit['context_spans']:assert norm(span['text']) in norm(expected[hit['doc_id']])
            answer=req('/api/chat',dict(question=question,session_id=name+'-'+str(len(result['checks']))))
            trace=req('/api/trace/'+answer['trace_id'])
            result['checks'].append(dict(question=question,gold=gold,fact=fact,answer=answer,trace=trace,retrieval=retrieval));save()
            if gold:
                assert any(x['doc_id']==gold and fact in x['text'] and x['score']>0 and not x['padded'] for x in hits),retrieval
                assert answer['answer_type']=='doc' and fact in answer['answer'],answer
                assert gold in {x['doc_id'] for x in answer['citations']}
                selected=next(s['detail']['selected'] for s in trace['steps'] if s['step']=='evidence')
                for cite in answer['citations']:
                    assert 0<len(norm(cite['quote']))<=400
                    assert norm(cite['quote']) in norm(expected[cite['doc_id']]),cite
                    assert any(s['doc_id']==cite['doc_id'] and any(h['chunk_id']==s['chunk_id'] and h['doc_id']==cite['doc_id'] and (norm(cite['quote']) in norm(h['text']) or any(norm(cite['quote']) in norm(t['text']) for t in h['context_spans'])) for h in hits) for s in selected),cite
            else:
                assert answer['answer_type']=='refusal' and not answer['citations'],answer
            assert not answer['data_evidence'],answer
            for old in stale:
                assert old not in answer['answer'] and old not in str(answer['citations']),answer
                assert all(old not in x['text'] for x in hits)
        assert before=={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in kb.iterdir() if f.is_file()}
    result['passed']=True;save()

def check(*args,**kwargs):
    try:check_strict(*args,**kwargs)
    except AssertionError as error:
        cases[-1]['error']=str(error);save()
        print(args[0], 'FAILED', str(error),flush=True)


try:
    aliases=lambda alias:'| 标准写法 | alias |\n|---|---|\n| 翡翠饭 | '+alias+' |'
    initial='翡翠饭的配送时限为31分钟。'
    write('KB-971.md',initial);write('KB-970.md',aliases('Ivory Bowl'))
    check('initial',{'KB-970':aliases('Ivory Bowl'),'KB-971':initial},[('Ivory Bowl的配送时限是多少分钟？','KB-971','31')])
    added='夜班配送申请应提前19小时提交。'
    write('KB-972.html','<html><head><style>hiddenstyle</style></head><body><p>'+added+'</p><script>hiddenjs</script></body></html>')
    check('add-html',{'KB-970':aliases('Ivory Bowl'),'KB-971':initial,'KB-972':added},[('夜班配送申请应提前多少小时提交？','KB-972','19')])
    changed='翡翠饭的配送时限为47分钟。'
    write('KB-970.md',aliases('Copper Dish'));(rt.kb/'KB-971.md').unlink();write('KB-971.txt',changed,'gbk')
    check('modify-format-encoding-alias',{'KB-970':aliases('Copper Dish'),'KB-971':changed,'KB-972':added},[('Copper Dish的配送时限是多少分钟？','KB-971','47'),('Ivory Bowl',None,None)],stale=('31分钟',))
    (rt.kb/'KB-972.html').unlink()
    check('delete',{'KB-970':aliases('Copper Dish'),'KB-971':changed},[('夜班配送申请应提前多少小时提交？',None,None)],stale=('19小时','31分钟'))
    other=out/'replacement-kb';other.mkdir();rt.env['KB_DIR']=str(other)
    new='夜班配送申请应提前29小时提交。'
    write('KB-973.txt',new,'gbk');write('README.md','非知识文档')
    check('switch-directory',{'KB-973':new},[('夜班配送申请应提前多少小时提交？','KB-973','29'),('Copper Dish',None,None)],stale=('19小时','47分钟','31分钟'))
    (out/'result.json').write_text(json.dumps(dict(passed=all(c['passed'] for c in cases),stages=len(cases),questions=sum(len(c['checks']) for c in cases)),indent=2))
finally:save()
assert all(c['passed'] for c in cases), 'Knowledge-base lifecycle has recorded failures'
