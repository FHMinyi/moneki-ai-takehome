"""Owned merged-source HTTP/browser harness. All model responses are controlled."""
import json,sys,threading,tempfile,shutil,socket,subprocess,time,os
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'docs/verification/g3-02'))
from test_http import m
from controlled_annotations import binding_for
OUT=Path(os.environ.get('G302_INTEGRATION_OUT',str(Path(__file__).parent)))
DEFAULT={'tool':'query_metrics','params':{'start':'2026-06-01','end':'2026-06-30','store_id':'S02'},'metric':'net_revenue'}
state=dict(DEFAULT);requests=[]
class Model(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,payload,status=200):
  raw=json.dumps(payload,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
  try:self.wfile.write(raw)
  except (BrokenPipeError,ConnectionResetError):pass
 def do_GET(self):self.send({'requests':len(requests),'case':state})
 def do_POST(self):
  global state
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  if self.path=='/case':state={**DEFAULT,**body};self.send({'ok':True});return
  if self.path!='/controlled/chat/completions':self.send({'error':'unexpected path'},404);return
  active=dict(state);requests.append(body)
  if active.get('status'):self.send({'error':{'message':'controlled failure'}},active['status']);return
  messages=body['messages'];last_user=max(i for i,x in enumerate(messages) if x['role']=='user')
  q=messages[last_user]['content'].split('\n（用户显式附加每日趋势引用')[0]
  results=[x for x in messages[last_user:] if x['role']=='tool']
  msg={'role':'assistant','content':'','reasoning_content':'CONTROLLED_INTEGRATION_ONLY'}
  if active.get('no_tools'):msg['content']=active['content']
  elif not results:
   if active.get('delay'):time.sleep(active['delay'])
   tool='search_kb' if active.get('mode')=='doc' else active['tool']
   params={'query':q,'top_k':5} if tool=='search_kb' and active.get('mode')=='doc' else active['params']
   msg['tool_calls']=[{'id':'controlled-call','type':'function','function':{'name':tool,'arguments':json.dumps(params)}}]
  elif 'content' in active:msg['content']=active['content']
  elif active.get('mode')=='doc':
   result=json.loads(results[-1]['content'])['result']
   e=next(e for e in result['evidence'] if e['doc_id']=='KB-013' and '24' in e['quote'])
   msg['content']=json.dumps({'answer_type':'doc','facts':[{'evidence_id':e['evidence_id'],'binding':binding_for(q,e)}]})
  else:msg['content']=json.dumps({'answer_type':'data','results':[{'call_id':'controlled-call','metric':active['metric']}]})
  self.send({'choices':[{'finish_reason':'tool_calls' if 'tool_calls' in msg else 'stop','message':msg}],'usage':{'prompt_tokens':1,'completion_tokens':1}})

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 assert not (OUT/'server-resources.json').exists(), 'Use a fresh G302_INTEGRATION_OUT; never replace a running/evidence manifest'
 work=Path(tempfile.mkdtemp(prefix='moneki-g302-integrated-'));r=m.Runtime(work,'integrated')
 shutil.copytree(ROOT/'knowledge_base',r.kb,dirs_exist_ok=True);r.build();shutil.copytree(ROOT/'frontend/dist',work/'frontend/dist')
 model=ThreadingHTTPServer(('127.0.0.1',0),Model);threading.Thread(target=model.serve_forever,daemon=True).start()
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 r.env.update(LLM_BASE_URL=f'http://127.0.0.1:{model.server_port}/controlled',LLM_API_KEY='integration-dummy',LLM_MODEL='controlled')
 with (work/'service.txt').open('w') as log:
  p=subprocess.Popen([str(ROOT/'starter/.venv/bin/python'),'-m','uvicorn','kbqa.server:app','--port',str(port)],cwd=r.source,env=r.env,stdout=log,stderr=log)
  record={'work':str(work),'api_pid':p.pid,'api_port':port,'model_port':model.server_port,'base':f'http://127.0.0.1:{port}','model':f'http://127.0.0.1:{model.server_port}','commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'controlled_only':True}
  (OUT/'server-resources.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
  try:
   while True:time.sleep(1)
  finally:p.terminate();p.wait(timeout=10);model.shutdown();model.server_close()
if __name__=='__main__':main()
