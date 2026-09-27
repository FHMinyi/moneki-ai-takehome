"""Authorized G3-02 execution only: fixed official provider, 8 CNY / 6 chats (initially 4; two individually authorized same-question retries).

Every outbound attempt reserves 2.20 CNY BEFORE sending. Complete usage releases
the difference at peak cache-miss prices; missing usage keeps the entire reserve.
No balance/model-list probes. Ledger is reused, never reset by this runner.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import httpx

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent/'live'
OUT.mkdir(exist_ok=True)
ledger_path=OUT/'ledger.json'
ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'chat_count':0,'calls':[],'limit_cny':8,'chat_limit':4,'billing_confirmed':False}
lock=threading.Lock()
def save():
    ledger['conservative_committed_cny']=sum(c['accounted_cny'] for c in ledger['calls'])
    ledger['remaining_cny']=8-ledger['conservative_committed_cny']
    ledger_path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
config={}
for line in (ROOT/'.env.live').read_text().splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        k,v=line.split('=',1);config[k.strip()]=v.strip().strip('\"\'')
assert config['LLM_BASE_URL'].rstrip('/')=='https://api.deepseek.com'
assert config['LLM_MODEL']=='deepseek-flash'
key=config['LLM_API_KEY']

class Proxy(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def respond(self,status,body):
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def do_POST(self):
        raw=self.rfile.read(int(self.headers['Content-Length']))
        body=json.loads(raw)
        if self.path!='/guard/chat/completions' or len(raw)>250000 or body.get('model')!='deepseek-flash' or body.get('max_tokens')!=4096:
            self.respond(400,b'{"error":{"message":"execution guard: configuration or size"}}');return
        with lock:
            reserved=sum(c['accounted_cny'] for c in ledger['calls'])
            if reserved+2.20>8 or sum(c['chat'] == ledger['chat_count'] for c in ledger['calls'])>=14:
                self.respond(402,b'{"error":{"message":"execution budget exhausted"}}');return
            entry={'chat':ledger['chat_count'],'attempt':len(ledger['calls'])+1,'request_bytes':len(raw),'accounted_cny':2.20,'status':'reserved','started_at':time.time()}
            ledger['calls'].append(entry);save()
        try:
            with httpx.Client(trust_env=False,timeout=125) as client:
                r=client.post('https://api.deepseek.com/chat/completions',json=body,headers={'Authorization':'Bearer '+key})
            # Only sanitized raw body is returned to the application trace.
            sanitized=r.text.replace(key,'[REDACTED]')
            usage=None
            try:usage=r.json().get('usage')
            except (ValueError,AttributeError):pass
            with lock:
                entry.update(status=r.status_code,elapsed_seconds=time.time()-entry['started_at'],usage=usage)
                if isinstance(usage,dict) and type(usage.get('prompt_tokens')) is int and type(usage.get('completion_tokens')) is int and usage['prompt_tokens']>=0 and usage['completion_tokens']>=0:
                    cost=(usage['prompt_tokens']*2+usage['completion_tokens']*8)/1_000_000
                    entry.update(accounted_cny=cost,peak_price_estimate_cny=cost)
                else:entry['note']='No complete usage; entire 2.20 CNY reserve retained.'
                save()
            self.respond(r.status_code,sanitized.encode())
        except Exception as exc:
            with lock:
                entry.update(status='transport_error',error_type=type(exc).__name__,note='No usage; entire reserve retained.');save()
            self.respond(503,b'{"error":{"message":"execution proxy transport failed"}}')

def request(url,body=None):
    req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=185) as response:return json.load(response)

def main():
    proxy=ThreadingHTTPServer(('127.0.0.1',0),Proxy)
    threading.Thread(target=proxy.serve_forever,daemon=True).start()
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    env={**os.environ,'LLM_BASE_URL':f'http://127.0.0.1:{proxy.server_port}/guard','LLM_API_KEY':'local-execution-dummy','LLM_MODEL':'deepseek-flash','VAR_DIR':'/tmp/moneki-g3-02-paid-var'}
    for name in ('DATA_DIR','KB_DIR'):env.pop(name,None)
    assert ledger['chat_count']==5, 'Only the user-authorized six-tool-round same-question retry remains'
    ledger.setdefault('authorization_updates', []).append({
      'from_chat_limit':5,'to_chat_limit':6,'amount_limit_unchanged':8,
      'source':'2026-09-27 user explicitly requested MAX_TOOL_ROUNDS 4 to 6 via coordinator 01a0dc94-4947-7a93-84b9-46b5c7249dfa; exactly one original identity-document question retry from shared 18-chat pool; no further retry.'})
    ledger['chat_limit']=6
    questions=['外卖退款是否要求顾客出示身份证？']
    with (OUT/'service.txt').open('a') as log:
        p=subprocess.Popen([str(ROOT/'starter/.venv/bin/python'),'-m','uvicorn','kbqa.server:app','--port',str(port)],cwd=ROOT/'starter',env=env,stdout=log,stderr=log)
        try:
            base=f'http://127.0.0.1:{port}'
            for _ in range(100):
                try:health=request(base+'/api/health');break
                except OSError:time.sleep(.1)
            assert health['llm_mode']=='live'
            assert not any(c.get('status')=='reserved' for c in ledger['calls']), 'Unresolved prior reservation'
            for question in questions:
                with lock:
                    assert ledger['chat_count']<6 and sum(c['accounted_cny'] for c in ledger['calls'])+2.20<=8
                    ledger['chat_count']+=1; n=ledger['chat_count'];save()
                response=request(base+'/api/chat',{'session_id':f'paid-{n}','question':question})
                trace=request(base+'/api/trace/'+response['trace_id'])
                result={'question':question,'response':response,'trace':trace,'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
                (OUT/f'chat-{n}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
                print(f'chat {n}: {response["answer_type"]}; {len(trace["llm_calls"])} model attempts',flush=True)
                if response['answer_type'] not in {'doc','refusal'}:break
        finally:
            p.terminate();p.wait(timeout=10)
            # Never release unknown calls on timeout; keep the ledger's reserve.
            proxy.shutdown();proxy.server_close()
            with lock:save()
    print(json.dumps({k:ledger[k] for k in ['chat_count','conservative_committed_cny','remaining_cny','billing_confirmed']},ensure_ascii=False))

if __name__=='__main__':main()
