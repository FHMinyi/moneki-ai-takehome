"""Reuse the unchanged G1 delivery assertions with isolated data and G3-only output."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[3]
HARNESS=ROOT/'docs/verification/g1-05'
OUT=Path(__file__).parent/'dashboard-delivery'
OUT.mkdir(exist_ok=True)
work=Path(tempfile.mkdtemp(prefix='moneki-g3-dashboard-'))
target=ROOT/'frontend/tests/g3-temporary-delivery.spec.ts'
assert not target.exists()
shutil.copyfile(HARNESS/'delivery.spec.ts',target)
records=[]
try:
    for kind in ('replacement','empty'):
        data=work/kind
        cmd=['python3',str(HARNESS/'fixture.py'),str(data),'--source',str(ROOT/'data/pos.db')]+(['--empty'] if kind=='empty' else [])
        subprocess.run(cmd,check=True,capture_output=True)
        digest=hashlib.sha256((data/'pos.db').read_bytes()).hexdigest()
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        env={**os.environ,'DATA_DIR':str(data),'VAR_DIR':str(work/(kind+'-var')),'LLM_API_KEY':'','LLM_BASE_URL':'','LLM_MODEL':''}
        with (OUT/(kind+'-service.txt')).open('w') as log:
            process=subprocess.Popen([str(ROOT/'starter/.venv/bin/python'),'-m','uvicorn','kbqa.server:app','--port',str(port)],cwd=ROOT/'starter',env=env,stdout=log,stderr=log)
            try:
                base=f'http://127.0.0.1:{port}'
                for _ in range(100):
                    try:urllib.request.urlopen(base+'/api/health',timeout=2).close();break
                    except OSError:time.sleep(.1)
                audit=subprocess.check_output(['python3',str(HARNESS/'audit_fixture.py'),'--base-url',base]+(['--empty'] if kind=='empty' else []),text=True)
                (OUT/(kind+'-audit.json')).write_text(audit)
                browser=['npm','--prefix','frontend','run','test:browser','--','g3-temporary-delivery.spec.ts','--workers=1']
                with (OUT/(kind+'-browser.txt')).open('w') as browser_log:
                    subprocess.run(browser,cwd=ROOT,env={**os.environ,'BROWSER_BASE_URL':base,'DELIVERY_CASE':kind,'DELIVERY_OUTPUT':str(OUT.resolve())},stdout=browser_log,stderr=subprocess.STDOUT,check=True)
                assert hashlib.sha256((data/'pos.db').read_bytes()).hexdigest()==digest
                records.append({'case':kind,'command':browser,'fixture_command':cmd,'fixture_sha256':digest,'fixture':str(data),'status':'passed'})
            finally:process.terminate();process.wait(timeout=10)
finally:target.unlink()
(OUT/'replacement-empty.json').write_text(json.dumps(records,indent=2)+'\n')
print('replacement 3 + empty 3 browser checks passed; fixture work:',work)
