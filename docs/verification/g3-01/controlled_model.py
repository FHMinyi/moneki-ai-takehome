"""Local controlled model. Only model outputs are controlled, never business results."""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT = {'tool':'query_metrics','params':{'start':'2026-06-01','end':'2026-06-30','store_id':'S02','product_id':'P06'},'metric':'qty'}
case = dict(DEFAULT)
requests = []

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def send(self, value, status=200):
        body=json.dumps(value,ensure_ascii=False).encode()
        ticks=int(getattr(self,'keepalive_seconds',0)*2)
        self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body)+ticks)); self.end_headers()
        try:
            for _ in range(ticks): self.wfile.write(b'\n'); self.wfile.flush(); time.sleep(.5)
            self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError): pass
    def do_GET(self):
        self.send({'requests':len(requests),'case':case})
    def do_POST(self):
        global case
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/case':
            case = {**DEFAULT, **body}; self.send({'ok':True}); return
        if self.path != '/controlled/chat/completions': self.send({'error':'wrong path'},404); return
        active=dict(case)
        self.keepalive_seconds=active.get('keepalive_seconds',0)
        requests.append(body)
        if active.get('status'): self.send({'error':{'message':'controlled error'}},active['status']); return
        messages=body['messages']
        start=max(i for i,m in enumerate(messages) if m['role']=='user')
        has_result=any(m['role']=='tool' for m in messages[start:])
        if not has_result and active.get('delay'): time.sleep(active['delay'])
        msg={'role':'assistant','content':'','reasoning_content':'CONTROLLED_PRIVATE_REASONING'}
        if active.get('no_tools'):
            msg['content']=active['content']
        elif not has_result:
            msg['tool_calls']=[{'id':'controlled-call','type':'function','function':{'name':active['tool'],'arguments':json.dumps(active['params'])}}]
        else:
            msg['content']=active.get('content',json.dumps({'answer_type':'data','results':[{'call_id':'controlled-call','metric':active['metric']}]}))
        self.send({'choices':[{'finish_reason':'stop' if has_result or active.get('no_tools') else 'tool_calls','message':msg}], 'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=9032); args=parser.parse_args()
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
