"""Compare body-shape reranking on actual candidates without mutating product code."""
import json,re,sys
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT
sys.path.insert(0,str(SOURCE/'starter'))
from kbqa.index import build_index
from kbqa.retriever import Retriever
from kbqa.entities import focus_kinds
from kbqa.docfacts import carries
index=build_index(ROOT/'knowledge_base')
r=Retriever(index,date(2026,9,1))
out=[]
for weight in [1.,1.5,2.,3.]:
 for q,doc in [('三文鱼那次断供供应商赔了多少钱','KB-022'),('S04 为什么不卖吞拿鱼三明治了','KB-029')]:
  result=r.search(q,top_k=5)
  kinds=focus_kinds(q)
  candidates=[]
  for c in result.candidates:
   if c['doc_id']!=doc:continue
   chunk=next(x for x in index.chunks if x.chunk_id==c['chunk_id'])
   matches=sum(carries(k,chunk.source_text) for k in kinds)
   score=c['score']*(weight if matches else 1.)
   candidates.append(dict(chunk_id=chunk.chunk_id,score=score,base=c['score'],matches=matches,text=chunk.source_text))
  candidates.sort(key=lambda c:-c['score'])
  out.append(dict(weight=weight,query=q,kinds=kinds,candidates=candidates))
Path(sys.argv[1]).write_text(json.dumps(out,ensure_ascii=False,indent=2))
for row in out:print(row['weight'],row['query'],row['candidates'][0]['chunk_id'],row['candidates'][0]['matches'],row['candidates'][0]['text'][:65])
