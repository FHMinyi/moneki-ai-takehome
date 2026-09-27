from pathlib import Path
import tempfile,subprocess,socket,time,json,urllib.request
from test_http import m,ROOT
import shutil
work=Path(tempfile.mkdtemp(prefix='moneki-g302-nokey-'));r=m.Runtime(work,'no-key')
shutil.copytree(ROOT/'knowledge_base',r.kb,dirs_exist_ok=True);r.build()
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
with (work/'server.log').open('w') as log:
 p=subprocess.Popen([str(ROOT/'starter/.venv/bin/python'),'-m','uvicorn','kbqa.server:app','--port',str(port)],cwd=r.source,env=r.env,stdout=log,stderr=log)
 try:
  for _ in range(100):
   try:urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health');break
   except OSError:time.sleep(.05)
  cmd=[str(ROOT/'starter/.venv/bin/python'),'eval/run_eval.py','--base-url',f'http://127.0.0.1:{port}','--questions','eval/public_questions.jsonl','--out','docs/verification/g3-02/no-key']
  result=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
  print(result.stdout,result.stderr)
  (ROOT/'docs/verification/g3-02/no-key-runtime.json').write_text(json.dumps({'work':str(work),'command':cmd,'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'exit_code':result.returncode,'service_pid':p.pid},indent=2))
 finally:p.terminate();p.wait(timeout=10)
raise SystemExit(result.returncode)
