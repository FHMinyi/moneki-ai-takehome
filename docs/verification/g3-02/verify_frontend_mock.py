"""Replay the three original workspace cases on their required no-Key service."""
import os,subprocess,tempfile,json,socket,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
work=Path(tempfile.mkdtemp(prefix='moneki-g302-front-mock-'))
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
env={**os.environ,'LLM_API_KEY':'','LLM_BASE_URL':'','LLM_MODEL':'','VAR_DIR':str(work/'var')}
with (work/'service.txt').open('w') as log:
 p=subprocess.Popen([str(ROOT/'starter/.venv/bin/python'),'-m','uvicorn','kbqa.server:app','--port',str(port)],cwd=ROOT/'starter',env=env,stdout=log,stderr=log)
 try:
  for _ in range(100):
   try:urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health');break
   except OSError:time.sleep(.05)
  cmd=['npx','playwright','test','tests/workspace.spec.ts','--grep','real API ledger','--workers=1','--output='+str(OUT/'frontend-mock-runtime')]
  result=subprocess.run(cmd,cwd=ROOT/'frontend',env={**os.environ,'BROWSER_BASE_URL':f'http://127.0.0.1:{port}','EVIDENCE_DIR':str(OUT/'frontend-mock')},capture_output=True,text=True)
  (OUT/'frontend-mock.txt').write_text(result.stdout+result.stderr)
  (OUT/'frontend-mock-resources.json').write_text(json.dumps({'work':str(work),'pid':p.pid,'port':port,'command':cmd,'exit_code':result.returncode,'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()},indent=2))
  print(result.stdout);assert result.returncode==0
 finally:p.terminate();p.wait(timeout=10)
