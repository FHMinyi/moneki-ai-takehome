import json,sys
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT
sys.path.insert(0,str(SOURCE/'starter'))
import kbqa.retriever as module
from kbqa.index import build_index
index=build_index(ROOT/'knowledge_base')
questions=[json.loads(l) for l in (ROOT/'eval/public_questions.jsonl').read_text().splitlines() if json.loads(l)['category']=='retrieval']
extra={'id':'alias-money','query':'鲑鱼波奇饭断供的赔付金额是多少','gold_all':['KB-022']}
rows=[]
for weight in [.6,1.,1.5,2.]:
 module.ALIAS_WEIGHT=weight
 r=module.Retriever(index,date(2026,9,1))
 outputs=[]
 for q in questions+[extra]:
  result=r.search(q['query'])
  ids={h.doc_id for h in result.ranked}
  passed=set(q.get('gold_all',[]))<=ids and (not q.get('gold_any') or bool(set(q['gold_any'])&ids))
  if q['id']=='alias-money':passed=passed and any(h.doc_id=='KB-022' and 'CNY' in h.source_text for h in result.ranked)
  outputs.append(dict(id=q['id'],passed=passed,trace=result.as_trace()))
 rows.append(dict(alias_weight=weight,passed=sum(q['passed'] for q in outputs),total=len(outputs),outputs=outputs))
 print(weight,rows[-1]['passed'])
Path(sys.argv[1]).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
