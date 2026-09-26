"""Preservation and own ephemeral process receipts; run only after checks finish."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];out=ROOT/'docs/verification/g2-03'
before=json.loads((out/'protected-before.json').read_text())
changed=[p for p,h in before.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
(out/'preservation.json').write_text(json.dumps(dict(checked=len(before),changed=changed),indent=2))
assert not changed,changed
services=[];db=[]
for path in sorted(out.rglob('*.json')):
 if path.name=='resources.json':continue
 payload=json.loads(path.read_text())
 if not isinstance(payload,dict):continue
 for record in payload.get('records',[]):
  if 'pid' in record:
   services.append(dict(evidence=str(path.relative_to(ROOT)),source=payload.get('source'),pid=record['pid'],port=record['port'],stopped=record.get('stopped')))
  if 'database_hash_before' in record:
   assert record['database_hash_before']==record['database_hash_after']
   db.append(dict(evidence=str(path.relative_to(ROOT)),before=record['database_hash_before'],after=record['database_hash_after']))
 if 'pid' in payload and 'port' in payload:
  services.append(dict(evidence=str(path.relative_to(ROOT)),source=payload.get('source'),pid=payload['pid'],port=payload['port'],stopped=payload.get('server_stopped')))
assert all(s['stopped'] for s in services)
result=dict(checkout=str(ROOT),branch='codex/g2-03-retrieval',managed_worktrees_created=0,services=services,service_runs=len(services),all_own_services_stopped=True,database_hash_checks=db,database_hash_checks_count=len(db),retained=['/tmp/moneki-g2-03-integration','/tmp/moneki-g2-03-final','pytest and export source paths recorded in evidence'],preexisting_untracked=['docs/baseline/2026-09-26-followup-draft.md','docs/research/'])
if (out/'experiment-replay.json').exists():
 result['experiment_exports']=[r['source'] for r in json.loads((out/'experiment-replay.json').read_text())]
(out/'resources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(dict(protected_files=len(before),changed=changed,service_runs=len(services),all_stopped=True,db_hash_checks=len(db))))
