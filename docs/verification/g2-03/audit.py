"""Audit exact rebuilt index + saved HTTP from baseline.py; no server or mocks."""
import json,sys
from pathlib import Path
run=Path(sys.argv[1]);out=Path(sys.argv[2])
env=json.loads((run/'environment.json').read_text())
payload=json.loads((Path(env['source'])/'starter/.cache/index.json').read_text())
chunks={c['chunk_id']:c for c in payload['chunks']}
rows=[]
for row in json.loads((run/'retrieval-responses.json').read_text()):
 q=row['question'];r=row['response'];hits=r['results']
 assert len(hits)==min(q['top_k'],len(chunks))
 assert [h['score'] for h in hits]==sorted([h['score'] for h in hits],reverse=True)
 for h in hits:
  c=chunks[h['chunk_id']];assert h['doc_id']==c['doc_id']
  assert h['text']==c['source_text']==payload['texts'][h['doc_id']][h['source_start']:h['source_end']]
  assert h['retrieval_text']==c['text'] and h['context_spans']==c['context_spans']
 valid=[h for h in hits if h['evidence_eligible'] and h['score']>0 and not h['padded']]
 ids={h['doc_id'] for h in valid}
 assert set(q.get('gold_all',[]))<=ids
 assert not q.get('gold_any') or bool(set(q['gold_any'])&ids)
 gold=set(q.get('gold_all',q.get('gold_any',[])))
 rows.append(dict(id=q['id'],query=q['query'],passed=True,gold_supported_hits=[h for h in valid if h['doc_id'] in gold],terms=r['diagnostics']['terms'],expansions=r['diagnostics']['expansions']))
# Evidence-level assertions supplement the unmodified public document-ID evaluator.
for question,word in [('R04','CNY'),('R10','低于')]:
 assert any(word in h['text'] for row in rows if row['id']==question for h in row['gold_supported_hits'])
result=dict(commit=env['commit'],documents=len(payload['docs']),chunks=len(chunks),queries=len(rows),passed=len(rows),http_identity_checks=sum(len(r['response']['results']) for r in json.loads((run/'retrieval-responses.json').read_text())),rows=rows)
out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
