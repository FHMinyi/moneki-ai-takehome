"""Independent saved-result audit: no network, no model calls."""
import json,re,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'live'
norm=lambda s:re.sub(r'[\s*`|#>]','',unicodedata.normalize('NFKC',s))
records=[]
for n,doc,expected in [(1,'KB-013','24'),(2,'KB-010','50'),(3,'KB-040','芝麻')]:
 d=json.loads((OUT/f'chat-{n}.json').read_text());a=d['response'];t=d['trace']
 assert a['answer_type']=='doc' and not a['data_evidence'] and expected in a['answer']
 assert {c['doc_id'] for c in a['citations']}=={doc}
 raw=next((ROOT/'knowledge_base').rglob(doc+'_*')).read_text()
 pool={e['evidence_id']:e for s in t['steps'] if s['step']=='tool' for e in s['detail']['result'].get('evidence',[])}
 for c in a['citations']:
  assert norm(c['quote']) in norm(raw) and 0<len(norm(c['quote']))<=400
  if c.get('evidence_id'):assert pool[c['evidence_id']]['quote']==c['quote']
 if n==2:assert a['citations'][0]['scope']['as_of']=='2026-02-01'
 records.append({'chat':n,'outcome':'supported doc','commit':d['commit']})
for n,error in [(4,'http_error'),(5,'tool_loop'),(6,'tool_loop'),(7,'data_binding')]:
 d=json.loads((OUT/f'chat-{n}.json').read_text());a=d['response']
 assert a['answer_type']=='refusal' and not a['citations'] and not a['data_evidence']
 assert any(error in e['message'] for e in d['trace']['errors'])
 records.append({'chat':n,'outcome':'engineering fallback; missing-attribute semantics NOT passed','error':error,'commit':d['commit'],'request_bytes':[len(json.dumps(c['request'],ensure_ascii=False).encode()) for c in d['trace']['llm_calls']]})
ledger=json.loads((OUT/'ledger.json').read_text());calls=ledger['calls']
assert len(calls)==25 and ledger['chat_count']==7 and all(c['status']==200 and c['usage'] for c in calls)
cost=sum((c['usage']['prompt_tokens']*2+c['usage']['completion_tokens']*8)/1e6 for c in calls)
assert abs(cost-ledger['conservative_committed_cny'])<1e-10
report={'records':records,'actual_outbound_calls':len(calls),'local_rejected_calls':1,'input_tokens':sum(c['usage']['prompt_tokens'] for c in calls),'output_tokens':sum(c['usage']['completion_tokens'] for c in calls),'peak_cache_miss_estimate_cny':round(cost,6),'billing_confirmed':False,'remaining_ticket_cny':round(8-cost,6),'g3_total_estimate_cny':round(cost+.047028,6),'g3_remaining_cny':round(50-cost-.047028,6),'pending_reservations':0}
(OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
