"""Rebuild actual corpus in memory per reversible lexical option; no cache writes."""
import json,re,sys
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'starter'))
from kbqa import tokenizer
scheme=sys.argv[1]
original=tokenizer.tokenize

def tokens(text):
    if scheme=='whitespace': return original(text)
    out=[]
    for run in re.findall(r'[\u3400-\u9fff]+|[a-z0-9]+',tokenizer.normalise(text)):
        if run.isascii(): out.append(run);continue
        if scheme in ('unigram','mixed'): out.extend(run)
        if scheme in ('bigram','mixed'): out.extend(run[i:i+2] for i in range(len(run)-1))
        if scheme=='bigram' and len(run)==1: out.append(run)
    return out

tokenizer.tokenize=tokens
from kbqa.index import build_index
from kbqa.retriever import Retriever
index=build_index(ROOT/'knowledge_base')
retriever=Retriever(index,date(2026,9,1))
rows=[]
for line in (ROOT/'eval/public_questions.jsonl').read_text().splitlines():
    q=json.loads(line)
    if q['category']!='retrieval':continue
    r=retriever.search(q['query'])
    ids={h.doc_id for h in r.ranked if h.score>0}
    passed=set(q.get('gold_all',[]))<=ids and (not q.get('gold_any') or bool(set(q['gold_any'])&ids))
    rows.append(dict(id=q['id'],passed=passed,query=q['query'],trace=r.as_trace()))
result=dict(scheme=scheme,passed=sum(r['passed'] for r in rows),total=len(rows),rows=rows)
Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(scheme,result['passed'],'/',result['total'])
