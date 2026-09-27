"""Controlled same-response minimal doc/data/mixed inputs for merged HTTP checks."""
import json,sys,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'docs/verification/g3-03'))
from http_harness import runtime
from test_mixed import CASES,QUESTIONS,choose
class Model(BaseHTTPRequestHandler):
 cases={QUESTIONS['H04']:dict(CASES['H04'])}
 def log_message(self,*a):pass
 def respond(self,p):
  raw=json.dumps(p,ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_POST(self):
  b=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  if self.path=='/case':type(self).cases[b['question']]=b['case'];self.respond(dict(ok=True));return
  q=next(m['content'] for m in reversed(b['messages']) if m['role']=='user').split('\n（',1)[0]
  c=type(self).cases[q];done=[json.loads(m['content']) for m in b['messages'] if m['role']=='tool'];calls=[];content=''
  if not done:
   if c['mode']=='doc':calls=[dict(id='kb',type='function',function=dict(name='search_kb',arguments=json.dumps(dict(query=c.get('query',q),top_k=10))))]
   else:
    calls=[dict(id='db',type='function',function=dict(name=c['tool'],arguments=json.dumps(c['params'])))]
    if c['mode']!='data':calls.append(dict(id='kb',type='function',function=dict(name='search_kb',arguments=json.dumps(dict(query=c.get('query',q),top_k=10)))))
  elif c['mode']=='doc':
   item=next(e for t in done for e in t['result'].get('evidence',[]) if e['doc_id']==c['doc'] and c['needle'] in e['quote'])
   content=json.dumps(dict(answer_type='doc',facts=[dict(evidence_id=item['evidence_id'])]))
  elif c['mode']=='data':content=json.dumps(dict(answer_type='data',results=[dict(call_id='db',metric=c['metric'])]))
  else:content=json.dumps(choose(c,[e for t in done for e in t['result'].get('evidence',[])]))
  msg=dict(role='assistant',content=content,reasoning_content='CONTROLLED_INTEGRATION_NOT_PROVIDER')
  if calls:msg['tool_calls']=calls
  self.respond(dict(choices=[dict(finish_reason='tool_calls' if calls else 'stop',message=msg)],usage=dict(prompt_tokens=0,completion_tokens=0)))
if __name__=='__main__':
 with runtime(sys.argv[1],handler=Model) as (_,r):
  print(json.dumps(r),flush=True)
  while True:time.sleep(1)
