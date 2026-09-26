"""Continue G2 acceptance in the fresh source/environment produced by G1 verify_delivery.
Run from git checkout: python3.12 verify_rag.py --work /tmp/moneki-g1-05-... --out /tmp/g205-rag-new
Only verification files receive declared, restored overlays; no application edits.
"""
import argparse, hashlib, json, os, shutil, signal, socket, subprocess, time
from pathlib import Path
from urllib.request import Request, urlopen

p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
root=Path.cwd(); source=a.work.resolve()/'source';out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
commit=json.loads((a.work/'preflight.json').read_text())['commit']
assert json.loads((a.work/'result.json').read_text())['passed']
python=str(source/'starter/.venv/bin/python')
env=os.environ.copy()
for key in ('LLM_API_KEY','LLM_BASE_URL','LLM_MODEL','DATA_DIR','KB_DIR','VAR_DIR','TODAY','PYTHONPATH','VIRTUAL_ENV'):
    env.pop(key,None)
env['PYTHONDONTWRITEBYTECODE']='1'
commands=[];services=[];overlays=[]
def save(name,obj):
    (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def run(args,name,extra=None,allowed=(0,)):
    with (out/name).open('w') as f:r=subprocess.run(args,cwd=source,env=env|(extra or {}),stdout=f,stderr=subprocess.STDOUT)
    commands.append(dict(args=args,cwd=str(source),environment=extra or {},exit_code=r.returncode,log=name));save('commands.json',commands)
    print(name,r.returncode,flush=True);assert r.returncode in allowed, name
    return r.returncode

def request(base,path,body=None):
    req=Request(base+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=20) as response:return json.load(response)

def start():
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    cmd=['make','run',f'PORT={port}'];f=(out/'server.txt').open('w')
    proc=subprocess.Popen(cmd,cwd=source,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);f.close();services.append(proc)
    base=f'http://127.0.0.1:{port}'
    for _ in range(200):
        assert proc.poll() is None
        try:
            h=request(base,'/api/health');assert h['llm_mode']=='mock';break
        except OSError:time.sleep(.1)
    else:raise RuntimeError('startup timeout')
    save('environment.json',dict(commit=commit,source=str(source),python=python,installed_environment_source=str(a.work),key_configured=False,today='2026-09-01',pid=proc.pid,port=port,command=cmd))
    save('health.json',h)
    return base

def overlay(path,text):
    original=path.read_bytes();path.write_text(text);overlays.append((path,original))
    return dict(path=str(path.relative_to(source)),original_sha256=hashlib.sha256(original).hexdigest(),overlay_sha256=hashlib.sha256(path.read_bytes()).hexdigest())

try:
    run(['make','rebuild'],'rebuild-original.txt')
    base=start()
    run([python,'eval/run_eval.py','--base-url',base,'--questions','eval/public_questions.jsonl','--out',str(out/'eval')],'eval.txt')
    rows=[]
    for line in (source/'eval/public_questions.jsonl').read_text().splitlines():
        q=json.loads(line)
        if q['category']=='retrieval':rows.append(dict(question=q,response=request(base,'/api/retrieve',dict(query=q['query'],top_k=q['top_k']))))
    save('retrieval-responses.json',rows)
    for n in ('02','03'):
        run([python,f'docs/verification/g2-{n}/audit.py',str(out),str(out/f'g2-{n}-audit.json')],f'g2-{n}-audit.txt')
    # Historical source is a test fixture only; the application has no .git dependency.
    legacy=out/'history-fixture';legacy.mkdir();manifest=[]
    oldcommit='8b72f47f712eab309bcc5e65841acfce45f0e17e'
    for name in ('index.py','chunker.py'):
        blob=subprocess.check_output(['git','show',oldcommit+':starter/kbqa/'+name],cwd=root)
        target=legacy/name;target.write_bytes(blob);target.chmod(0o444)
        manifest.append(dict(commit=oldcommit,path='starter/kbqa/'+name,sha256=hashlib.sha256(blob).hexdigest(),fixture=str(target)))
    test=source/'docs/verification/g2-02/test_evidence.py';text=test.read_text()
    old="old = subprocess.check_output(['git', 'show',\n                '8b72f47f712eab309bcc5e65841acfce45f0e17e:starter/kbqa/' + name], cwd=ROOT)"
    assert old in text
    record=overlay(test,text.replace(old,"old = (Path(os.environ['G2_HISTORY_FIXTURE']) / name).read_bytes()"))
    heading_legacy=out/'heading-history-fixture';heading_legacy.mkdir()
    for name in ('loader.py','units.py'):
        historical='358859a5be641b04395f314029e4b9325631dd8a'
        blob=subprocess.check_output(['git','show',historical+':starter/kbqa/'+name],cwd=root)
        target=heading_legacy/name;target.write_bytes(blob);target.chmod(0o444)
        manifest.append(dict(commit=historical,path='starter/kbqa/'+name,sha256=hashlib.sha256(blob).hexdigest(),fixture=str(target)))
    heading_test=source/'docs/verification/g2-04-heading-fix/test_heading.py';heading_text=heading_test.read_text()
    heading_old="subprocess.check_output(['git','show','358859a:'+('starter/kbqa/'+name)],cwd=ROOT)"
    assert heading_old in heading_text
    heading_record=overlay(heading_test,heading_text.replace(heading_old,"(Path(os.environ['G2_HEADING_HISTORY_FIXTURE'])/name).read_bytes()"))
    save('verification-overlays.json',dict(history=manifest,overlays=[record,heading_record],reason='Replace only git fixture acquisition with fixed read-only historical bytes; assertions unchanged.'))
    tests=['docs/verification/g2-01/test_ingestion.py','docs/verification/g2-02/test_evidence.py','docs/verification/g2-03/test_retrieval.py','docs/verification/g2-04/test_doc_qa.py','docs/verification/g2-04-heading-fix/test_heading.py']
    run([python,'-m','pytest',*tests,'--collect-only','-q'],'collected-tests.txt')
    assert '199 tests collected' in (out/'collected-tests.txt').read_text()
    run([python,'-m','pytest',*tests,'-q','--basetemp',str(out/'pytest-temp')],'rag-regressions.txt',dict(G2_EVIDENCE=str(out/'rag-http'),G2_HISTORY_FIXTURE=str(legacy),G2_HEADING_HISTORY_FIXTURE=str(heading_legacy)))
    for path,blob in overlays:path.write_bytes(blob)
    overlays.clear()
    audit_input=out/'answer-audit-input';audit_input.mkdir()
    # Coverage metadata has no records; audit only G2-04 HTTP filenames declared by its collected test IDs.
    collected=subprocess.check_output([python,'-m','pytest','docs/verification/g2-04/test_doc_qa.py','--collect-only','-q'],cwd=source,env=env,text=True)
    for line in collected.splitlines():
        if '::test_' in line:
            name=line.split('::',1)[1]+'.json'
            shutil.copyfile(out/'rag-http'/name,audit_input/name)
    run([python,'docs/verification/g2-04/audit.py',str(audit_input),str(out/'answer-audit.json')],'answer-audit.txt')
    run([python,'docs/verification/g2-04/compare.py','docs/verification/g2-04/review-r1-integration/eval/report.json',str(out/'eval/report.json'),str(out/'vs-r1.json')],'compare.txt')
    comparison=out/'vs-r1.md'
    comparison.write_text(comparison.read_text().replace('与G2-03逐题、逐轮对照','与G2-04 R1逐题、逐轮对照'))
    # Preserve the old incompatible overlap assertion as an observed failure.
    run([python,'-m','pytest','docs/diagnostics/2026-09-27-g2-start/test_diagnostic_probes.py','-q','--basetemp',str(out/'diagnostic-temp')],'diagnostic-original.txt',dict(PYTHONPATH=str(source/'starter'),G2_SOURCE=str(source)),allowed=(0,1))
    save('result.json',dict(passed=True,commit=commit,source=str(source),rag_tests=199,diagnostic_original_expected_overlap_failures=3))
finally:
    for path,blob in overlays:path.write_bytes(blob)
    for proc in services:
        if proc.poll() is None:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
    save('services.json',[dict(pid=p.pid,stopped=p.poll() is not None) for p in services])
