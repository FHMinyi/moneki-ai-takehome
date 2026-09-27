import json, os
from pathlib import Path
import httpx, pytest
from http_harness import runtime
from test_mixed import ROOT,CASES,QUESTIONS
OUT=Path(os.environ.get('G303_HTTP_OUT','/tmp/g303-http'));OUT.mkdir(parents=True,exist_ok=True)
@pytest.fixture(scope='module')
def server(tmp_path_factory):
 with runtime(tmp_path_factory.mktemp('g303-http')) as r:yield r
@pytest.mark.parametrize('qid',CASES)
def test_actual_http(server,qid):
 base,resources=server
 with httpx.Client(trust_env=False,timeout=180) as c:
  r=c.post(base+'/api/chat',json=dict(question=QUESTIONS[qid],session_id='g303-'+qid));assert r.status_code==200
  a=r.json();t=c.get(base+'/api/trace/'+a['trace_id']).json()
 (OUT/(qid+'.json')).write_text(json.dumps(dict(answer=a,trace=t,resources=resources),ensure_ascii=False,indent=2))
 assert a['answer_type']==('data' if qid=='H06' else 'hybrid'),a
 assert CASES[qid]['expected'] in a['answer']
 assert t['errors']==[]
 assert len(t['llm_calls'])==2
 assert 'G303_CONTROLLED' not in json.dumps(a)
 assert any(s['step']=='mixed_binding' for s in t['steps'])
 assert len(a['answer'])<=1200
 from kbqa.mixed_answer import compact
 assert all(len(compact(x['quote']))<=400 for x in a['citations'])
