"""Replay unchanged G2-05 checkpoint assertions against a selected source tree."""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];evidence=a.evidence.resolve();evidence.mkdir(parents=True,exist_ok=False)
work=Path(tempfile.mkdtemp(prefix='moneki-g204-heading-replay-'))
checkpoint='d2a25c2585f7eb680bbffa06577a40f5966cebe0';runs=[]
for filename,label in [('reproduce_heading.py','ab'),('verify_kb.py','lifecycle')]:
    data=subprocess.check_output(['git','show',checkpoint+':docs/verification/g2-05/'+filename],cwd=repo)
    script=work/filename;script.write_bytes(data)
    out=work/label;cmd=[sys.executable,str(script),'--source',str(a.source.resolve()),'--out',str(out)]
    result=subprocess.run(cmd,capture_output=True,text=True)
    target=evidence/label;target.mkdir()
    (target/'stdout.txt').write_text(result.stdout);(target/'stderr.txt').write_text(result.stderr)
    for name in ['http.json','result.json','inputs','input-snapshots']:
        src=out/name
        if src.is_dir():shutil.copytree(src,target/name)
        elif src.exists():shutil.copy2(src,target/name)
    runs.append(dict(script=filename,checkpoint=checkpoint,sha256=hashlib.sha256(data).hexdigest(),command=cmd,exit_code=result.returncode,work=str(out)))
(evidence/'commands.json').write_text(json.dumps(dict(source=str(a.source.resolve()),application_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.source,text=True).strip(),runs=runs),ensure_ascii=False,indent=2))
print(json.dumps(runs,ensure_ascii=False,indent=2))
raise SystemExit(int(any(x['exit_code'] for x in runs)))
