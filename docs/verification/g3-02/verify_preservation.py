"""NUL-safe fixed-point verification; never modifies originals or initial manifest."""
from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
FIXED='587ae820185cd10839e189efa9fb2ed8863d1ca5'
def main():
 old=json.loads((ROOT/'docs/verification/g3-01/protected-before.json').read_text())
 initial=json.loads((OUT/'protected-before.json').read_text())['files']
 missing=[p for p in old if not (ROOT/p).is_file()]
 changed=[p for p,v in old.items() if (ROOT/p).is_file() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=v]
 entries=subprocess.check_output(['git','ls-tree','-rz',FIXED],cwd=ROOT).split(b'\0');selected=[];oids=[]
 for row in entries:
  if not row:continue
  meta,path=row.split(b'\t',1);p=path.decode()
  if p.startswith(('data/','knowledge_base/','eval/','docs/baseline/','docs/verification/')):
   selected.append(p);oids.append(meta.split()[2].decode())
 bad=[]
 for i in range(0,len(selected),200):
  paths=selected[i:i+200];valid=[p for p in paths if (ROOT/p).is_file()]
  got=subprocess.check_output(['git','hash-object','--no-filters',*valid],cwd=ROOT,text=True).splitlines()
  actual=dict(zip(valid,got))
  bad.extend(p for p,oid in zip(paths,oids[i:i+200]) if actual.get(p)!=oid)
 exception='docs/baseline/2026-09-26-followup-draft.md'
 report={'initial_manifest_count':len(initial),'predecessor_manifest_count':len(old),
  'predecessor_missing_now':missing,'predecessor_changed_now':changed,
  'authorized_external_exception':{'path':exception,'original_sha256':initial[exception],
   'confirmation':'2026-09-27 user confirmed deletion/move via coordinating chat 01a0dc94-4947-7a93-84b9-46b5c7249dfa. Do not restore.'},
  'unexpected_missing':[p for p in missing if p!=exception],
  'initial_omitted_predecessor_count':len(set(old)-set(initial)),
  'cause':'Initial git ls-files lacked -z: quoted non-ASCII/backslash names skipped by prefix filter. Original incomplete 2434 manifest remains unchanged; current audit compares predecessor SHA256 and all fixed-point protected Git blobs with NUL-safe paths.',
  'fixed_point':FIXED,'fixed_point_protected_tracked_count':len(selected),'fixed_point_differences':bad,
  'research_unchanged':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in initial.items() if p.startswith('docs/research/')}}
 (OUT/'preservation-final.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps(report,ensure_ascii=False))
 assert not bad and not changed and not report['unexpected_missing'] and all(report['research_unchanged'].values())
if __name__=='__main__':main()
