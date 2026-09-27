"""Real HTTP model transport with controlled selections, and real FastAPI/tools."""
import json, os, socket, subprocess, sys, tempfile, threading, time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import httpx
from test_mixed import ROOT, CASES, QUESTIONS, choose

class Controlled(BaseHTTPRequestHandler):
 extra_cases={}
 def log_message(self,*args):pass
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  messages=body['messages'];question=next(m['content'] for m in reversed(messages) if m['role']=='user')
  qid=next((q for q in CASES if QUESTIONS[q] in question),None)
  extra=type(self).extra_cases.get(question)
  if not qid and not extra:
   content=json.dumps(dict(answer_type='refusal',reason='insufficient_evidence'));calls=[]
  else:
   c=extra or CASES[qid];done=[json.loads(m['content']) for m in messages if m['role']=='tool']
   if not done:
    calls=[dict(id='db',type='function',function=dict(name=c['tool'],arguments=json.dumps(c['params']))),dict(id='kb',type='function',function=dict(name='search_kb',arguments=json.dumps(dict(query=c.get('query',question),top_k=10))))];content=''
   else:
    items=[e for t in done for e in t['result'].get('evidence',[])]
    content=json.dumps(choose(c,items));calls=[]
  msg=dict(role='assistant',content=content,reasoning_content='G303_CONTROLLED_NOT_REAL_MODEL')
  if calls:msg['tool_calls']=calls
  raw=json.dumps(dict(choices=[dict(finish_reason='tool_calls' if calls else 'stop',message=msg)],usage=dict(prompt_tokens=1,completion_tokens=1))).encode()
  self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

@contextmanager
def runtime(path,data_dir=None,kb_dir=None):
 path=Path(path);path.mkdir(parents=True,exist_ok=True)
 model=ThreadingHTTPServer(('127.0.0.1',0),Controlled);threading.Thread(target=model.serve_forever,daemon=True).start()
 api_port=port();base=f'http://127.0.0.1:{api_port}'
 env={**os.environ,'VAR_DIR':str(path/'var'),'LLM_BASE_URL':f'http://127.0.0.1:{model.server_port}/controlled','LLM_API_KEY':'controlled-not-a-secret','LLM_MODEL':'controlled','PYTHONPATH':str(ROOT/'starter')}
 if data_dir:env['DATA_DIR']=str(data_dir)
 if kb_dir:env['KB_DIR']=str(kb_dir)
 log=(path/'server.log').open('w');p=subprocess.Popen([sys.executable,'-m','uvicorn','kbqa.server:app','--host','127.0.0.1','--port',str(api_port)],cwd=ROOT/'starter',env=env,stdout=log,stderr=log)
 record=dict(pid=p.pid,harness_pid=os.getpid(),api_port=api_port,model_port=model.server_port,base_url=base,worktree=str(ROOT),var=str(path/'var'))
 try:
  with httpx.Client(trust_env=False,timeout=180) as client:
   for _ in range(120):
    try:
     if client.get(base+'/api/health').status_code==200:break
    except httpx.TransportError:pass
    time.sleep(.05)
   else:raise RuntimeError('server not ready')
  (path/'resources.json').write_text(json.dumps(record,indent=2));yield base,record
 finally:
  p.terminate();p.wait(timeout=10);log.close();model.shutdown();model.server_close()

if __name__=='__main__':
 path=Path(sys.argv[1]) if len(sys.argv)>1 else Path(tempfile.mkdtemp(prefix='g303-browser-'))
 with runtime(path) as (base,record):
  print(json.dumps(record),flush=True)
  while True:time.sleep(1)
