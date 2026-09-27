import json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(os.environ['G303_NOKEY_OUT']);OUT.mkdir(parents=True,exist_ok=False)
work=Path(tempfile.mkdtemp(prefix='g303-nokey-'))
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
env={**os.environ,'LLM_API_KEY':'','LLM_BASE_URL':'','LLM_MODEL':'','VAR_DIR':str(work/'var'),'PYTHONPATH':str(ROOT/'starter')}
with (work/'server.log').open('w') as log:
 p=subprocess.Popen([sys.executable,'-m','uvicorn','kbqa.server:app','--port',str(port)],cwd=ROOT/'starter',env=env,stdout=log,stderr=log)
 try:
  with httpx.Client(trust_env=False) as client:
   for _ in range(100):
    try:
     health=client.get(f'http://127.0.0.1:{port}/api/health').json();break
    except httpx.TransportError:time.sleep(.05)
  command=[sys.executable,'eval/run_eval.py','--base-url',f'http://127.0.0.1:{port}','--questions','eval/public_questions.jsonl','--out',str(OUT/'eval')]
  r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True)
  (OUT/'stdout.txt').write_text(r.stdout+r.stderr)
  (OUT/'runtime.json').write_text(json.dumps(dict(work=str(work),command=command,commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),health=health,exit_code=r.returncode,pid=p.pid,stopped=True),indent=2))
  print(r.stdout[-3000:]);print(r.stderr)
 finally:p.terminate();p.wait(timeout=10)
