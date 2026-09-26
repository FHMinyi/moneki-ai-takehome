import os,sys,json,subprocess,tempfile,pathlib,time,urllib.request,hashlib,socket
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--repo',type=pathlib.Path,required=True)
parser.add_argument('--out',type=pathlib.Path,required=True)
args=parser.parse_args()
ROOT=args.repo.resolve()
OUT=args.out.resolve()
OUT.mkdir(parents=True,exist_ok=False)
TMP=pathlib.Path(tempfile.mkdtemp(prefix='moneki-g2-source-'))
PYTHON=ROOT/'starter/.venv/bin/python'
paths=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths if p and (ROOT/p).is_file()}
(OUT/'protected-before.json').write_text(json.dumps(hashes,indent=2))
archive=subprocess.check_output(['git','archive','HEAD'],cwd=ROOT)
subprocess.run(['tar','-x','-C',str(TMP)],input=archive,check=True)
env=os.environ.copy()
for key in ['LLM_API_KEY','LLM_BASE_URL','LLM_MODEL','DATA_DIR','KB_DIR','VAR_DIR','TODAY','PYTHONPATH']:
    env.pop(key,None)
env['PYTHONPATH']=str(TMP/'starter')
meta={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source':str(TMP),'python':str(PYTHON),'key_configured':False,'runtime_reused':True,'source_export':'git archive HEAD','commands':[]}
for name,args in [('rebuild',[str(PYTHON),'-m','kbqa.rebuild']),('backend-tests',[str(PYTHON),'-m','pytest','tests','-q'])]:
    with (OUT/(name+'.txt')).open('w') as f:
        r=subprocess.run(args,cwd=TMP/'starter',env=env,stdout=f,stderr=subprocess.STDOUT)
    meta['commands'].append({'args':args,'cwd':str(TMP/'starter'),'exit_code':r.returncode})
# Tests have isolated fixtures; start a separate process with the real implementation.
with socket.socket() as s:
    s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
base=f'http://127.0.0.1:{port}'
log=(OUT/'server.log').open('w')
proc=subprocess.Popen([str(PYTHON),'-m','uvicorn','kbqa.server:app','--host','127.0.0.1','--port',str(port)],cwd=TMP/'starter',env=env,stdout=log,stderr=subprocess.STDOUT)
meta.update(port=port,pid=proc.pid)
def request(path,data=None):
    req=urllib.request.Request(base+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as resp:return json.load(resp)
try:
    for _ in range(100):
        try:
            health=request('/api/health');break
        except Exception:
            if proc.poll() is not None:raise RuntimeError('server exited')
            time.sleep(.1)
    else:raise RuntimeError('startup timeout')
    (OUT/'health.json').write_text(json.dumps(health,ensure_ascii=False,indent=2))
    args=[str(PYTHON),'eval/run_eval.py','--base-url',base,'--questions','eval/public_questions.jsonl','--out',str(OUT/'eval')]
    with (OUT/'eval.stdout.txt').open('w') as f:r=subprocess.run(args,cwd=TMP,env=env,stdout=f,stderr=subprocess.STDOUT)
    meta['commands'].append({'args':args,'cwd':str(TMP),'exit_code':r.returncode})
    results=[]
    for line in (TMP/'eval/public_questions.jsonl').read_text().splitlines():
        q=json.loads(line)
        if q['category']=='retrieval': results.append({'question':q,'response':request('/api/retrieve',{'query':q['query'],'top_k':q['top_k']})})
    (OUT/'retrieval-responses.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
finally:
    proc.terminate()
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()
    log.close()
    meta['server_stopped']=proc.poll() is not None
    (OUT/'environment.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    changed=[p for p,h in hashes.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    (OUT/'preservation.json').write_text(json.dumps({'checked':len(hashes),'changed':changed},indent=2))
print(json.dumps(meta,ensure_ascii=False))
print((OUT/'eval/report.md').read_text().split('## 没通过的题')[0])
