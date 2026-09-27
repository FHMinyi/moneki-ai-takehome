"""P14 equivalent at /api/chat: identical tools/data, only wire pacing differs."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent/'keepalive';OUT.mkdir(exist_ok=True)
def request(url,body=None):
    req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=185) as r:return json.load(r)
def ask(base,name):
    body={'session_id':name,'question':'S02六月牛肉poke卖了多少份？'}
    started=time.monotonic();response=request(base+'/api/chat',body);elapsed=time.monotonic()-started
    trace=request(base+'/api/trace/'+response['trace_id'])
    data={'request':body,'response':response,'trace':trace,'elapsed_seconds':elapsed}
    (OUT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return data
request('http://127.0.0.1:9032/case',{})
normal=ask('http://127.0.0.1:8032','normal')
request('http://127.0.0.1:9032/case',{'keepalive_seconds':18})
slow=ask('http://127.0.0.1:8032','slow')
assert normal['response']['answer_type']==slow['response']['answer_type']=='data'
assert normal['response']['answer']==slow['response']['answer']
assert normal['response']['data_evidence']==slow['response']['data_evidence']
assert '销量 417 件' in slow['response']['answer']
assert slow['elapsed_seconds']>=36 and normal['elapsed_seconds']<5
assert len(slow['trace']['llm_calls'])==2
assert all(c['raw_response'].startswith('\n') for c in slow['trace']['llm_calls'])
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
env={**os.environ,'LLM_BASE_URL':'http://127.0.0.1:9032/controlled','LLM_API_KEY':'controlled-dummy','LLM_MODEL':'controlled','VAR_DIR':'/tmp/moneki-g3-01-budget-var','CHAT_BUDGET':'12'}
with (OUT/'budget-service.txt').open('w') as log:
    process=subprocess.Popen([str(ROOT/'starter/.venv/bin/python'),'-m','uvicorn','kbqa.server:app','--port',str(port)],cwd=ROOT/'starter',env=env,stdout=log,stderr=log)
    try:
        base=f'http://127.0.0.1:{port}'
        for _ in range(100):
            try:request(base+'/api/health');break
            except OSError:time.sleep(.1)
        expired=ask(base,'budget-12s')
        assert expired['response']['answer_type']=='refusal'
        assert 11<expired['elapsed_seconds']<14
        assert expired['trace']['llm_calls'][0]['error']=='timeout'
    finally:process.terminate();process.wait(timeout=10)
request('http://127.0.0.1:9032/case',{})
(OUT/'result.json').write_text(json.dumps({'status':'passed','official_P14':'SKIP','normal_seconds':normal['elapsed_seconds'],'slow_seconds':slow['elapsed_seconds'],'budget_seconds':expired['elapsed_seconds'],'slow_keepalive_seconds_per_model_response':18,'command':'starter/.venv/bin/python docs/verification/g3-01/verify_keepalive.py'},indent=2)+'\n')
print('normal/slow complete data chain and total deadline refusal passed')
