"""Reproduce G1-05 against a committed source export. No installed environment is copied.
Run from repo root: python3.12 docs/verification/g1-05/verify_delivery.py --commit <sha>
Default stops all services. --keep-original retains only original on 8015 for review.
"""
import argparse, hashlib, json, os, platform, shutil, signal, socket, subprocess, tempfile, time
from pathlib import Path
from urllib.request import urlopen

ROOT=Path.cwd(); HARNESS=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--prepared',type=Path);p.add_argument('--keep-original',action='store_true');a=p.parse_args()
commit=subprocess.check_output(['git','rev-parse',a.commit],text=True).strip()
work=a.prepared or Path(tempfile.mkdtemp(prefix='moneki-g1-05-',dir='/tmp'))
source=work/'source'; env=os.environ.copy()
for k in ('LLM_API_KEY','LLM_BASE_URL','LLM_MODEL','DATA_DIR','KB_DIR','VAR_DIR','TODAY'):env.pop(k,None)
for port in (8015,8016,8017):
    with socket.socket() as sock: sock.bind(('127.0.0.1',port))
absent=['starter/.venv','frontend/node_modules','frontend/dist','starter/var','starter/.cache','.env.live','starter/.env.live']
commands=[];services=[]
def run(args,log,extra=None):
    commands.append(dict(command=args,cwd=str(source),log=log,extra_env=extra or {}))
    (work/'commands.json').write_text(json.dumps(commands,indent=2))
    with (work/log).open('w') as f: subprocess.run(args,cwd=source,env=env| (extra or {}),stdout=f,stderr=subprocess.STDOUT,check=True)
    print(log+' PASS',flush=True)
def start(port,extra=None):
    args=['make','run',f'PORT={port}']
    if extra:args += [f'{k}={v}' for k,v in extra.items()]
    log=(work/f'service-{port}.txt').open('a')
    proc=subprocess.Popen(args,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);log.close();services.append(proc)
    (work/f'process-{port}.json').write_text(json.dumps(dict(pid=proc.pid,pgid=proc.pid,port=port,command=args,cwd=str(source)),indent=2))
    for _ in range(100):
        if proc.poll() is not None:raise RuntimeError(f'Service {port} exited')
        try:
            health=json.load(urlopen(f'http://127.0.0.1:{port}/api/health',timeout=2));assert health['llm_mode']=='mock';return proc
        except OSError:time.sleep(.2)
    raise RuntimeError('Service failed to become healthy')
def stop(proc):
    if proc.poll() is None:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
    services.remove(proc)
def hashes():
    files=subprocess.check_output(['git','ls-files','-z'],text=True).split('\0')
    paths=[ROOT/f for f in files if f and f.startswith(('data/','knowledge_base/','docs/baseline/','docs/verification/')) and not f.startswith('docs/verification/g1-05/')]
    paths += [ROOT/'docs/baseline/2026-09-26-followup-draft.md',*(ROOT/'docs/research').rglob('*')]
    return {str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths if f.is_file()}
before=hashes(); (work/'protected-before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2))
try:
    if not a.prepared:
        source.mkdir(); archive=subprocess.Popen(['git','archive',commit],stdout=subprocess.PIPE)
        subprocess.run(['tar','-x','-C',str(source)],stdin=archive.stdout,check=True);assert archive.wait()==0
        assert all(not (source/f).exists() for f in absent)
        (work/'preflight.json').write_text(json.dumps(dict(commit=commit,source=str(source),absent=absent,clean=True),indent=2))
        run(['make','setup'],'setup.txt');run(['make','rebuild'],'rebuild-original.txt')
    else:
        assert json.loads((work/'preflight.json').read_text())['commit']==commit
    versions={k:subprocess.check_output(v,env=env,text=True).strip() for k,v in {'python':['python3.12','--version'],'node':['node','--version'],'npm':['npm','--version'],'make':['make','--version']}.items()}
    versions.update(platform=platform.platform(),commit=commit,llm_mode='mock',llm_variables='all three removed; no dotenv loader',source=str(source))
    (work/'environment.json').write_text(json.dumps(versions,indent=2))
    run(['starter/.venv/bin/python','-m','pip','freeze'],'python-dependencies.txt')
    run(['starter/.venv/bin/python','-m','pytest','starter/tests','-q'],'backend-tests.txt')
    run(['npm','--prefix','frontend','run','typecheck'],'typecheck.txt')
    # Verification-only overlay. Application files remain exactly at commit above.
    shutil.copyfile(HARNESS/'delivery.spec.ts',source/'frontend/tests/g1-05-delivery.spec.ts')
    proc=start(8015)
    run(['python3.12','eval/run_eval.py','--base-url','http://127.0.0.1:8015','--questions','eval/public_questions.jsonl','--only','metrics','--out',str(work/'metrics')],'metrics.txt')
    run(['sh',str(HARNESS/'run_browser.sh')],'browser-original.txt',dict(BROWSER_BASE_URL='http://127.0.0.1:8015',G1_OUTPUT=str(work/'old-browser'),DELIVERY_CASE='original',DELIVERY_OUTPUT=str(work/'screenshots')))
    original_health=json.load(urlopen('http://127.0.0.1:8015/api/health'));original_quality=json.load(urlopen('http://127.0.0.1:8015/api/data_quality'))
    assert original_health['valid_sales_rows']==original_quality['cleaning_report']['kept_rows']==18290
    assert original_quality['cleaning_report']['raw_rows']==18628
    assert list(original_quality['cleaning_report']['removed'].values())==[8,150,30,10,40,100]
    assert original_quality['data_period']==dict(start='2026-05-01',end='2026-08-31')
    (work/'original-health-quality.json').write_text(json.dumps(dict(health=original_health,quality=original_quality),ensure_ascii=False,indent=2))
    stop(proc)
    for kind,port in [('replacement',8016),('empty',8017)]:
        data=work/f'{kind}-data'; var=work/f'{kind}-var';empty=['--empty'] if kind=='empty' else []
        run(['python3.12',str(HARNESS/'fixture.py'),str(data),'--source',str(source/'data/pos.db'),*empty],f'fixture-{kind}.txt')
        fixture_hash=hashlib.sha256((data/'pos.db').read_bytes()).hexdigest()
        run(['make','rebuild',f'DATA_DIR={data}',f'VAR_DIR={var}'],f'rebuild-{kind}.txt')
        proc=start(port,dict(DATA_DIR=str(data),VAR_DIR=str(var)))
        run(['python3.12',str(HARNESS/'audit_fixture.py'),'--base-url',f'http://127.0.0.1:{port}',*empty],f'audit-{kind}.json')
        run(['sh',str(HARNESS/'run_browser.sh'),'g1-05-delivery.spec.ts'],f'browser-{kind}.txt',dict(BROWSER_BASE_URL=f'http://127.0.0.1:{port}',G1_OUTPUT=str(work/f'browser-{kind}'),DELIVERY_CASE=kind,DELIVERY_OUTPUT=str(work/'screenshots')))
        assert hashlib.sha256((data/'pos.db').read_bytes()).hexdigest()==fixture_hash
        stop(proc)
    assert before==hashes()
    (work/'preservation.json').write_text(json.dumps(dict(passed=True,count=len(before),files=before),ensure_ascii=False,indent=2))
    artifacts={str(f.relative_to(source)):dict(bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for pattern in ['starter/var/clean.db','starter/.cache/index.json','frontend/dist/**/*'] for f in source.glob(pattern) if f.is_file()}
    (work/'generated-artifacts.json').write_text(json.dumps(artifacts,indent=2))
    # Every tracked source/input byte must still match the exported commit.
    checked=0
    for entry in subprocess.check_output(['git','ls-tree','-rz',commit],cwd=ROOT).split(b'\0'):
        if not entry:continue
        meta,name=entry.split(b'\t',1);content=(source/name.decode()).read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        assert blob==meta.decode().split()[2], name.decode()
        checked+=1
    overlay=source/'frontend/tests/g1-05-delivery.spec.ts'
    (work/'tested-tree.json').write_text(json.dumps(dict(commit=commit,tracked_files_checked=checked,all_exported_tracked_bytes_match=True,verification_overlay=str(overlay.relative_to(source)),overlay_sha256=hashlib.sha256(overlay.read_bytes()).hexdigest()),indent=2))
    if a.keep_original:proc=start(8015);services.remove(proc)
    (work/'result.json').write_text(json.dumps(dict(passed=True,commit=commit,work=str(work),retained_port=8015 if a.keep_original else None),indent=2))
    print('COMPLETE '+str(work),flush=True)
finally:
    for proc in list(services):stop(proc)
