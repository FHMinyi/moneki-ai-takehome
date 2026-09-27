"""Read-only preservation, lineage, contract and usage audit."""
import hashlib,json,subprocess,sys,os,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'starter'))
from kbqa.live import _numbers_in
from kbqa.mixed_answer import compact

def main():
 before=json.loads((OUT/'protected-before.json').read_text())
 changed=[p for p,h in before.items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
 assert not changed,changed
 ledger=json.loads((OUT/'live/ledger.json').read_text());assert ledger['chat_count']==4 and len(ledger['calls'])==11
 total=0;tokens=[0,0]
 for call in ledger['calls']:
  assert call['status']==200 and call['usage'] and call['accounted_cny']<2.2
  u=call['usage'];cost=(u['prompt_tokens']*2+u['completion_tokens']*8)/1_000_000
  assert cost==call['accounted_cny'];total+=cost;tokens[0]+=u['prompt_tokens'];tokens[1]+=u['completion_tokens']
  raw=json.loads((OUT/f"live/api-{call['attempt']}.json").read_text())
  assert raw['request']['model']=='deepseek-flash' and raw['request']['max_tokens']==4096
  assert json.loads(raw['response'])['usage']==u
 assert abs(total-.223182)<1e-9
 chats=[]
 for n in range(1,5):
  p=json.loads((OUT/f'live/chat-{n}.json').read_text());a=p['response'];t=p['trace']
  assert len(a['answer'])<=1200 and len(set(_numbers_in(a['answer'])))<=20
  pool={e['evidence_id']:e for s in t['steps'] if s['step']=='document_evidence' for e in s['detail']['evidence']}
  for c in a['citations']:
   assert c['evidence_id'] in pool and c['quote']==pool[c['evidence_id']]['quote'] and len(compact(c['quote']))<=400
  assert len(t['llm_calls'])==sum(c['chat']==n for c in ledger['calls'])
  chats.append(dict(chat=n,commit=p['commit'],answer_type=a['answer_type'],api_calls=len(t['llm_calls']),errors=[e['message'] for e in t['errors']]))
 # Read the existing credential locally, report only whether any artifact leaked it.
 key=None
 for line in Path('/Volumes/MACPSSD/project/moneki-ai-takehome/.env.live').read_text().splitlines():
  if line.startswith('LLM_API_KEY='):key=line.split('=',1)[1].strip().strip('"\'')
 assert key
 leaks=[str(p.relative_to(ROOT)) for p in OUT.rglob('*') if p.is_file() and key.encode() in p.read_bytes()]
 assert not leaks
 report=dict(business_sha=json.loads((OUT/'fixed-source-delivery.json').read_text())['business_sha'],protected_count=len(before),protected_changes=changed,credential_leaks=leaks,chats=chats,actual_api_count=11,prompt_tokens=tokens[0],completion_tokens=tokens[1],peak_cache_miss_estimate_cny=round(total,6),billing_confirmed=False,pending_reserves=0,other_g3_estimate_reported_by_coordinator=1.217374,total_g3_estimate_cny=round(total+1.217374,6),directed_pool_used_after_this_ticket=13)
 Path(os.environ.get('G303_AUDIT_OUT',str(Path(tempfile.mkdtemp(prefix='g303-audit-'))/'audit.json'))).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='chats'},ensure_ascii=False))
if __name__=='__main__':main()
