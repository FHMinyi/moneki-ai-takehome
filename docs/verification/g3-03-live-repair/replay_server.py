"""Network-only local replay of saved successful provider messages, no upstream."""
import copy,json,os,socket,subprocess,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from contextlib import contextmanager
import httpx
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
SAVED={p.stem:json.loads(p.read_text()) for p in (HERE/'original').glob('*.json')}

def sig(e):return json.dumps({k:v for k,v in e.items() if k!='evidence_id'},ensure_ascii=False,sort_keys=True)
class Model(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  question=next(m['content'] for m in reversed(body['messages']) if m['role']=='user').split('\n（',1)[0]
  saved=next((v for v in SAVED.values() if v['chat']['request']['question']==question),None)
  if not saved:raise AssertionError('Unconfigured replay question')
  trace=saved['trace']['response'];round_index=sum(m['role']=='assistant' for m in body['messages'])
  original=trace['llm_calls'][round_index]['response']['choices'][0]
  choice=copy.deepcopy(original);msg=choice['message'];mapping={}
  if not msg.get('tool_calls'):
   actual=[e for m in body['messages'] if m['role']=='tool' for e in json.loads(m['content'])['result'].get('evidence',[])]
   lookup={sig(e):e['evidence_id'] for e in actual}
   olds=[e for s in trace['steps'] if s['step']=='document_evidence' for e in s['detail']['evidence']]
   for e in olds:
    if sig(e) in lookup:mapping[e['evidence_id']]=lookup[sig(e)]
   payload=json.loads(msg['content'])
   for fact in payload.get('facts',[]):fact['evidence_id']=mapping[fact['evidence_id']]
   msg['content']=json.dumps(payload,ensure_ascii=False)
  raw=json.dumps({'choices':[choice],'usage':{'prompt_tokens':0,'completion_tokens':0},'model':'saved-response-replay'},ensure_ascii=False).encode()
  self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

@contextmanager
def runtime(path):
 path=Path(path);path.mkdir(parents=True,exist_ok=True)
 model=ThreadingHTTPServer(('127.0.0.1',0),Model);threading.Thread(target=model.serve_forever,daemon=True).start()
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 env={**os.environ,'PYTHONPATH':str(ROOT/'starter'),'VAR_DIR':str(path/'var'),'DATA_DIR':str(ROOT/'data'),'KB_DIR':str(ROOT/'knowledge_base'),'LLM_BASE_URL':f'http://127.0.0.1:{model.server_port}/replay','LLM_API_KEY':'local-replay-only','LLM_MODEL':'saved-response-replay'}
 log=(path/'server.log').open('w');p=subprocess.Popen([sys.executable,'-m','uvicorn','kbqa.server:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT/'starter',env=env,stdout=log,stderr=log)
 base=f'http://127.0.0.1:{port}';resources=dict(base=base,api_pid=p.pid,model_pid=os.getpid(),api_port=port,model_port=model.server_port,var=str(path/'var'),worktree=str(ROOT),mode='FREE_SAVED_PROVIDER_REPLAY_NO_UPSTREAM')
 try:
  with httpx.Client(trust_env=False,timeout=180) as c:
   for _ in range(100):
    try:
     if c.get(base+'/api/health').status_code==200:break
    except httpx.TransportError:time.sleep(.05)
  (path/'resources.json').write_text(json.dumps(resources,indent=2)+'\n');yield base,resources
 finally:p.terminate();p.wait(timeout=10);model.shutdown();model.server_close();log.close()
if __name__=='__main__':
 with runtime(sys.argv[1]) as (_,resources):
  print(json.dumps(resources),flush=True)
  while True:time.sleep(1)
