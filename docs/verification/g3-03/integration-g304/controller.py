"""Controlled model HTTP; only integration test inputs, no provider calls."""
import json,sys,threading,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler
HERE=Path(__file__).parent;sys.path.insert(0,str(HERE.parent))
from http_harness import runtime
from test_mixed import CASES,QUESTIONS,choose

class Model(BaseHTTPRequestHandler):
 cases={QUESTIONS[q]:dict(CASES[q]) for q in CASES}
 entered=threading.Event()
 def log_message(self,*a):pass
 def respond(self,p):
  raw=json.dumps(p,ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_POST(self):
  b=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  if self.path=='/case':type(self).cases[b['question']]=b['case'];self.respond(dict(ok=True));return
  msgs=b['messages'];q=next(m['content'] for m in reversed(msgs) if m['role']=='user').split('\n（',1)[0]
  case=type(self).cases.get(q,dict(content=dict(answer_type='refusal',reason='insufficient_evidence')))
  done=[json.loads(m['content']) for m in msgs if m['role']=='tool']
  rounds=sum(bool(m.get('tool_calls')) for m in msgs if m['role']=='assistant')
  calls=[];content=''
  if case.get('immediate'):content=json.dumps(case['content'])
  elif not done:
   type(self).entered.set()
   if case.get('delay'):time.sleep(case['delay'])
   if 'tool' not in case:content=json.dumps(case.get('content',dict(answer_type='refusal',reason='insufficient_evidence')))
   else:
    calls=[dict(id='db',type='function',function=dict(name=case['tool'],arguments=json.dumps(case['params'])))]
    if case.get('mode') in {'target','anomaly','payment','price'}:calls.append(dict(id='kb',type='function',function=dict(name='search_kb',arguments=json.dumps(dict(query=case.get('query',q),top_k=10)))))
  elif rounds<case.get('rounds',1) and b.get('tool_choice')!='none':
   calls=[dict(id=f'kb-{rounds}',type='function',function=dict(name='search_kb',arguments=json.dumps(dict(query=case.get('query',q),top_k=10))))]
  elif case.get('content'):content=json.dumps(case['content'])
  elif case.get('mode')=='data':content=json.dumps(dict(answer_type='data',results=[dict(call_id='db',metric=case['metric'])]))
  else:content=json.dumps(choose(case,[e for t in done for e in t['result'].get('evidence',[])]))
  msg=dict(role='assistant',content=content,reasoning_content='G303_G304_CONTROLLED_ONLY')
  if calls:msg['tool_calls']=calls
  self.respond(dict(choices=[dict(finish_reason='tool_calls' if calls else 'stop',message=msg)],usage=dict(prompt_tokens=1,completion_tokens=1)))

if __name__=='__main__':
 with runtime(Path(sys.argv[1]),handler=Model) as (_,resources):
  print(json.dumps(resources),flush=True)
  while True:time.sleep(1)
