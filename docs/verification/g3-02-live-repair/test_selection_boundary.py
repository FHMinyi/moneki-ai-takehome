"""New contract: semantic selection is model-owned, source integrity is code-owned."""
from evidence_io import read_jsonl
import json,sys,copy
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import pytest
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'starter'))
sys.path.insert(0,str(ROOT/'docs/verification/g3-02'))
from kbqa.config import load_settings
from kbqa.service import Service
from kbqa.document_evidence import DocumentEvidence
from kbqa.trace import Trace
from kbqa.llm import LLMError,LLMClient
import os,tempfile
os.environ.setdefault('G302_HTTP_OUT',tempfile.mkdtemp(prefix='g302-http-evidence-'))
from test_http import runtime,chat
ROWS=read_jsonl(HERE/'chat-trace.jsonl')
CASES=json.loads((HERE/'finalise-red.json').read_text())['results']

def original(case):
 trace=next(r['response'] for r in ROWS if r['chat']==case['chat'] and r['path'].startswith('/api/trace/'))
 items={e['evidence_id']:e for s in trace['steps'] if s['step']=='document_evidence' for e in s['detail']['evidence']}
 chosen=[items[r['evidence_id']] for r in json.loads(case['content'])['facts']]
 return trace,chosen

@pytest.fixture(scope='module')
def service(tmp_path_factory):return Service(replace(load_settings(),var_dir=tmp_path_factory.mktemp('selection'),llm_api_key='',llm_base_url='',llm_model=''))

@pytest.mark.parametrize('case',CASES,ids=lambda c:c['case'])
def test_saved_content_unchanged(service,case):
 trace,chosen=original(case);pool=DocumentEvidence(service.facts);pool.add(copy.deepcopy(chosen))
 with patch.object(LLMClient,'_post',side_effect=AssertionError('No provider calls')):
  answer=pool.render(case['content'],case['question'],Trace('replay',case['question']))
 assert answer.answer_type=='doc'
 for c in answer.citations:assert c['quote']==service.facts.index.texts[c['doc_id']][c['source_start']:c['source_end']]

@pytest.mark.parametrize('case',CASES,ids=lambda c:c['case'])
def test_minimal_protocol_real_http(tmp_path,case):
 trace,chosen=original(case)
 query=None
 for step in trace['steps']:
  if step['step']=='search':query=step['detail']['query']
  if step['step']=='document_evidence' and any(e['evidence_id']==chosen[0]['evidence_id'] for e in step['detail']['evidence']):break
 assert query
 def select(result):
  refs=[]
  for old in chosen:
   found=next(e for e in result['evidence'] if e['doc_id']==old['doc_id'] and e['quote']==old['quote'])
   refs.append({'evidence_id':found['evidence_id']})
  return json.dumps({'answer_type':'doc','facts':refs})
 with runtime(tmp_path,{'selector':select,'params':{'query':query,'top_k':10}}) as (r,serve,payload):
  with serve() as request:answer,t=chat(request,case['question'])
 assert answer['answer_type']=='doc',answer
 assert len(t['llm_calls'])==2
 assert all(c['quote']==payload['texts'][c['doc_id']][c['source_start']:c['source_end']] for c in answer['citations'])
 assert all(call['request']['max_tokens']==8192 for call in t['llm_calls'])
 assert all(call['request']['model']=='controlled' for call in t['llm_calls'])

@pytest.mark.parametrize('mutation',['offset','quote','number','context','metadata','chunk','swapped_columns','unknown_id','duplicate','free_answer','free_value','too_many','table_header'])
def test_forgery_or_structure_rejected(service,mutation):
 case=CASES[1] if mutation in ('table_header','swapped_columns') else CASES[0]
 _,chosen=original(case);pool=DocumentEvidence(service.facts);pool.add(copy.deepcopy(chosen))
 item=next(iter(pool.items.values()));payload={'answer_type':'doc','facts':[{'evidence_id':item['evidence_id']}]}
 if mutation=='chunk':item['chunk_id']='KB-013#9999'
 if mutation=='swapped_columns':
  cells=item['quote'].split('|');cells[3],cells[5]=cells[5],cells[3];item['quote']='|'.join(cells)
 if mutation=='offset':item['source_start']+=1
 if mutation=='quote':item['quote']='任意伪造政策'
 if mutation=='number':item['quote']=item['quote'].replace('24','99')
 if mutation=='context':item['context'][0]['quote']='# forged heading'
 if mutation=='metadata':item['metadata']['title']='伪造标题'
 if mutation=='unknown_id':payload['facts'][0]['evidence_id']='doc-not-retrieved'
 if mutation=='duplicate':payload['facts']*=2
 if mutation=='free_answer':payload['answer']='退款需要手续费99元'
 if mutation=='free_value':payload['facts'][0]['value']=99
 if mutation=='too_many':payload['facts']*=5
 if mutation=='table_header':item['context']=[c for c in item['context'] if not c['quote'].strip().startswith('|')]
 with pytest.raises(LLMError):pool.render(json.dumps(payload),case['question'],Trace('bad','bad'))


def test_explicit_scope_conflicts(service):
 case=CASES[0];_,chosen=original(case);pool=DocumentEvidence(service.facts);pool.add(copy.deepcopy(chosen))
 item=next(iter(pool.items.values()));content=json.dumps({'answer_type':'doc','facts':[{'evidence_id':item['evidence_id']}]})
 plan=service.planner.plan('2026年1月1日的退款政策')
 from datetime import date
 plan.as_of=date(2026,1,1)
 with pytest.raises(LLMError,match='尚未生效'):pool.render(content,plan.question,Trace('scope',plan.question),plan=plan)


def test_legacy_binding_is_ignored_never_rendered(service):
 case=CASES[0];_,chosen=original(case);pool=DocumentEvidence(service.facts);pool.add(copy.deepcopy(chosen))
 item=next(iter(pool.items.values()));trace=Trace('legacy',case['question'])
 payload={'answer_type':'doc','facts':[{'evidence_id':item['evidence_id'],'binding':{'supported':True,'answer':'需付9999999元'}}]}
 answer=pool.render(json.dumps(payload),case['question'],trace)
 assert '9999999' not in answer.answer
 assert trace.steps[-1]['detail']['legacy_bindings_ignored']==1
 assert trace.steps[-1]['detail']['semantic_selection']=='same_model'


def test_explicit_store_scope_is_not_model_owned(service):
 case=CASES[0];_,chosen=original(case)
 # Real metadata fixture in a new KB avoids inventing applicability on old data.
 from tempfile import TemporaryDirectory
 with TemporaryDirectory() as directory:
  root=Path(directory);kb=root/'kb';kb.mkdir()
  (kb/'KB-998.md').write_text('---\ntitle: 配送标准\neffective_from: 2026-01-01\nstores: [S01]\n---\n配送须在31分钟内完成。')
  local=Service(replace(load_settings(),kb_dir=kb,var_dir=root/'var',llm_api_key='',llm_base_url='',llm_model=''))
  from kbqa.trace import Trace
  plan=local.planner.plan('S01配送标准')
  result=local.retriever.search('配送标准',top_k=5,store_id='S01',as_of=plan.as_of)
  pool=DocumentEvidence(local.facts,result)
  item=next(iter(pool.items.values()))
  assert item['metadata']['stores_explicit']
  plan.store_id='S02'
  with pytest.raises(LLMError,match='门店'):
   pool.render(json.dumps({'answer_type':'doc','facts':[{'evidence_id':item['evidence_id']}]}),plan.question,Trace('scope',plan.question),plan=plan)
