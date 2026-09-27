import json,os
from pathlib import Path
import httpx,pytest
from replay_server import runtime,SAVED
OUT=Path(os.environ.get('G303_REPAIR_HTTP','/tmp/g303-live-repair-http'));OUT.mkdir(parents=True,exist_ok=True)
@pytest.fixture(scope='module')
def server(tmp_path_factory):
 with runtime(tmp_path_factory.mktemp('mixed-repair-http')) as r:yield r

@pytest.mark.parametrize('qid',['C07','T02-1','H04','T03-2'])
def test_saved_choice_over_actual_http(server,qid):
 base,resources=server;sid='saved-'+qid;records=[]
 order=['T03-1-context',qid] if qid=='T03-2' else [qid]
 with httpx.Client(trust_env=False,timeout=180) as c:
  for key in order:
   q=SAVED[key]['chat']['request']['question'];r=c.post(base+'/api/chat',json=dict(session_id=sid,question=q));assert r.status_code==200
   a=r.json();t=c.get(base+'/api/trace/'+a['trace_id']).json();records.append(dict(question=q,response=a,trace=t))
 (OUT/(qid+'.json')).write_text(json.dumps(dict(records=records,resources=resources,mode='local network replay; no provider calls'),ensure_ascii=False,indent=2)+'\n')
 assert a['answer_type']=='hybrid' and not t['errors'],a
 assert a['data_evidence'] and a['citations']
 if qid=='C07':assert '35%' in a['answer'] and '补充数据对照' in a['answer']
 if qid=='T02-1':assert '质检不合格' in a['answer']
 if qid=='H04':assert {'KB-025','KB-001'}<={x['doc_id'] for x in a['citations']}
 if qid=='T03-2':assert '适用门店：S02' in a['answer'] and 'S03 实收单价 42.00' in a['answer'] and 'S05 实收单价 42.00' in a['answer']
 assert 'local-replay-only' not in json.dumps(t)
