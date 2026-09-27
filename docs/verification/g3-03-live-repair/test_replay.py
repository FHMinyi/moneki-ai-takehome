"""Saved provider selections, fresh actual SQLite/retrieval; never a live retry."""
import json,os,sys
from pathlib import Path
from datetime import date
from dataclasses import replace
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'starter'))
from kbqa.service import Service
from kbqa.config import load_settings
from kbqa.document_evidence import DocumentEvidence
from kbqa.mixed_answer import render_mixed
from kbqa.trace import Trace
HERE=Path(__file__).parent

@pytest.fixture(scope='module')
def service(tmp_path_factory):
 return Service(replace(load_settings(),var_dir=tmp_path_factory.mktemp('mixed-repair'),llm_base_url='',llm_api_key='',llm_model=''))

def prepared(service,qid):
 saved=json.loads((HERE/'original'/f'{qid}.json').read_text());t=saved['trace']['response'];raw=next(s['detail'] for s in t['steps'] if s['step']=='plan')
 plan=service.planner.plan(raw['standalone_question'])
 for key in ['question','search_query','intent','kind','year','store_id','product_id','metric','needs_data','needs_docs']:
  setattr(plan,key,raw[key])
 plan.standalone=raw['standalone_question'];plan.window=tuple(raw['window']) if raw['window'] else None;plan.compare_window=tuple(raw['compare_window']) if raw['compare_window'] else None;plan.as_of=date.fromisoformat(raw['as_of'])
 evidence=[];pool=DocumentEvidence(service.facts)
 for step in t['steps']:
  if step['step']!='tool':continue
  d=step['detail'];actual=service.run_tool(d['tool'],d['params'],plan=plan) if d['tool']=='search_kb' else service.run_tool(d['tool'],d['params'])
  assert 'error' not in actual
  if d['tool']=='search_kb':
   # The index identity includes the absolute KB directory. Preserve original
   # response IDs only after proving every other evidence field equals a fresh
   # local retrieval. This is replay-fixture provenance, not product aliases.
   signature=lambda e:json.dumps({k:v for k,v in e.items() if k!='evidence_id'},ensure_ascii=False,sort_keys=True)
   fresh={signature(e):e for e in actual['evidence']}
   for old in d['result']['evidence']:
    assert signature(old) in fresh,(qid,old['doc_id'],old['quote'])
   pool.add(d['result']['evidence'])
  else:
   assert actual==d['result'],(qid,d['tool'])
   evidence.append(dict(_call_id=d['call_id'],tool=d['tool'],params=d['params'],result=actual))
 payload=json.loads(t['llm_calls'][-1]['response']['choices'][0]['message']['content'])
 assert all(f['evidence_id'] in pool.items for f in payload['facts'])
 return plan,evidence,pool,payload

@pytest.mark.parametrize('qid',['C07','T02-1','H04','T03-2'])
def test_original_selection_replay(service,qid):
 plan,ev,pool,payload=prepared(service,qid);trace=Trace('free-replay-'+qid,plan.question)
 answer=render_mixed(payload,ev,pool,plan,service.catalog,trace,search_performed=True)
 assert answer.answer_type=='hybrid',answer
 if qid=='C07':assert '35%' in answer.answer and any(c['doc_id']=='KB-029' for c in answer.citations)
 if qid=='T02-1':assert '质检不合格' in answer.answer and answer.data_evidence[0]['result']['period_b']['qty']==0
 if qid=='H04':
  assert '45.00' in answer.answer and '42.00' in answer.answer
  assert {'KB-025','KB-001'}<={c['doc_id'] for c in answer.citations}
 if qid=='T03-2':
  assert all(s in answer.answer for s in ['S02','S03','S05','29.00','42.00'])
  assert '全部门店售价为 29' not in answer.answer
 output=os.environ.get('G303_REPAIR_OUT')
 if output:
  out=Path(output);out.mkdir(parents=True,exist_ok=True)
  (out/(qid+'.json')).write_text(json.dumps(dict(answer=answer.__dict__,steps=trace.steps,source='saved original selection, freshly reexecuted local tools; no provider retry'),ensure_ascii=False,indent=2)+'\n')
