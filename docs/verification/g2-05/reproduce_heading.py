"""Minimal real rebuild/HTTP A-B: implicit title must not swallow real prose.
Run with the clean export's newly installed Python. No production edits.
Expected: both canonical and alias questions return the authored 31-minute fact
with a continuous KB-971 quote, whether or not an explicit heading exists.
"""
import argparse, hashlib, importlib.util, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
source=a.source.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location('runtime',source/'docs/verification/g2-03/test_retrieval.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rt=m.Runtime(out,'heading-ab');results=[]
alias='| 标准写法 | alias |\n|---|---|\n| 翡翠饭 | Ivory Bowl |'
fact='翡翠饭的配送时限为31分钟。'
try:
    for stage,header in [('no-heading',''),('explicit-heading','# 配送规范\n\n')]:
        (rt.kb/'KB-970.md').write_text(alias);(rt.kb/'KB-971.md').write_text(header+fact)
        snap=out/'inputs'/stage;snap.mkdir(parents=True)
        for file in rt.kb.iterdir():(snap/file.name).write_bytes(file.read_bytes())
        rt.build()
        with rt.serve() as req:
            for n,query in enumerate(['翡翠饭的配送时限是多少分钟？','Ivory Bowl的配送时限是多少分钟？']):
                hits=req('/api/retrieve',dict(query=query,top_k=5))
                answer=req('/api/chat',dict(question=query,session_id=stage+str(n)))
                trace=req('/api/trace/'+answer['trace_id'])
                retrieve_ok=any(h['doc_id']=='KB-971' and fact in h['text'] and h['text'] in header+fact and h['score']>0 and not h['padded'] for h in hits['results'])
                chat_ok=answer['answer_type']=='doc' and '31分钟' in answer['answer'] and dict(doc_id='KB-971',quote=fact) in answer['citations']
                results.append(dict(stage=stage,question=query,expected=fact,retrieve_passed=retrieve_ok,chat_passed=chat_ok,answer=answer,trace=trace))
finally:
    (out/'http.json').write_text(json.dumps(dict(source=str(rt.source),records=rt.records,results=results),ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k not in ('answer','trace')} for r in results],ensure_ascii=False,indent=2))
assert all(r['retrieve_passed'] and r['chat_passed'] for r in results), 'Real prose was rejected in the recorded no-heading case'
