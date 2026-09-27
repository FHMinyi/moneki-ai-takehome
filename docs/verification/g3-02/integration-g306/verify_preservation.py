"""Check incoming-main protected blobs, and preserve paid/history records."""
import json,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).parent
snapshot=json.loads((OUT/'protected-main.json').read_text());expected=snapshot['git_blobs'];changed=[]
paths=list(expected)
for i in range(0,len(paths),200):
 batch=paths[i:i+200];present=[p for p in batch if (ROOT/p).is_file()]
 hashes=subprocess.check_output(['git','hash-object','--no-filters',*present],cwd=ROOT,text=True).splitlines()
 actual=dict(zip(present,hashes));changed.extend(p for p in batch if actual.get(p)!=expected[p])
paid=[f'docs/verification/g3-02/live/chat-{i}.json' for i in range(1,8)]+['docs/verification/g3-02/live/ledger.json']
paid_unchanged=all((ROOT/p).read_bytes()==subprocess.check_output(['git','show','0644f99:'+p],cwd=ROOT) for p in paid)
report={'incoming_main':snapshot['commit'],'protected_count':len(expected),'changed':changed,'g302_paid_records_unchanged':paid_unchanged,'g306_files':sum(p.startswith('docs/verification/g3-06/') for p in expected),'scope':'all incoming main data/KB/eval/baseline/verification tracked files; plus frozen G302 paid records'}
(OUT/'preservation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
assert not changed and paid_unchanged
