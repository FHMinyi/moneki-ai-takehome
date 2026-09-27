import json,sys
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'starter'))
from kbqa.service import Service
from kbqa.config import load_settings
from kbqa.document_evidence import DocumentEvidence
from kbqa.live import LiveEngine
from kbqa.trace import Trace
from kbqa.llm import LLMError,LLMClient

@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
 s=Service(replace(load_settings(),var_dir=tmp_path_factory.mktemp('envelope'),llm_base_url='',llm_api_key='',llm_model=''))
 path=ROOT/'docs/verification/g3-05/optional-5b6a4ca/eval-live/chat-trace.jsonl'
 t=next(r['response'] for r in map(json.loads,path.open()) if r.get('chat')==37 and r.get('path','').startswith('/api/trace/'))
 pool=DocumentEvidence(s.facts)
 for step in t['steps']:
  if step['step']=='document_evidence':
   for e in step['detail']['evidence']:
    source=s.facts.index.texts[e['doc_id']]
    for span in [e,*e['context']]:assert source[span['source_start']:span['source_end']]==span['quote']
   pool.add(step['detail']['evidence'])
 content=t['llm_calls'][-1]['response']['choices'][0]['message']['content']
 engine=LiveEngine(None,s.answerer,s.run_tool,'2026-09-01',s.data_period)
 return s,engine,pool,content,t

def finish(prepared,content,evidence=None):
 s,e,p,_,t=prepared
 with patch.object(LLMClient,'_post',side_effect=AssertionError('paid forbidden')):
  return e._finalise(s.planner.plan(t['question']),content,evidence or [],p,Trace('offline-s01',t['question']))

def test_saved_s01(prepared):
 a=finish(prepared,prepared[3]);assert a.answer_type=='doc'
 assert any(c['doc_id']=='KB-060' and '12' in c['quote'] for c in a.citations)

@pytest.mark.parametrize('opening',['```json','```'])
def test_doc_wrappers(prepared,opening):
 a=finish(prepared,opening+'\n'+json.dumps({'answer_type':'doc','facts':[{'evidence_id':'doc-938f12744447cf0f3706'}]})+'\n```')
 assert a.answer_type=='doc'

@pytest.mark.parametrize('content',[
 'prefix\n```json\n{}\n```','```json\n{}\n```\nsuffix','```json\n{}\n```\n```json\n{}\n```',
 '```python\n{}\n```','```json\n{broken}\n```','[]','null','{"a":1} {"b":2}',
 '```json\n{"answer_type":"doc","facts":[{"evidence_id":"fake"}]}\n```',
 '```json\n{"answer_type":"doc","facts":[{"evidence_id":"doc-938f12744447cf0f3706"}],"answer":"invented"}\n```'])
def test_invalid_rejected(prepared,content):
 with pytest.raises(LLMError):finish(prepared,content)

def test_fenced_data_reaches_renderer(prepared):
 s=prepared[0];params={'start':'2026-08-01','end':'2026-08-01','store_id':'S01'}
 result=s.run_tool('query_metrics',params)
 a=finish(prepared,'```json\n{"answer_type":"data","results":[{"call_id":"real","metric":"net_revenue"}]}\n```',[{'_call_id':'real','tool':'query_metrics','params':params,'result':result}])
 assert a.answer_type=='data' and a.data_evidence[0]['result']==result

@pytest.mark.parametrize('content', ['{broken}', '[]'])
def test_accurate_format_errors(prepared,content):
 with pytest.raises(LLMError,match='answer_json'):finish(prepared,content)
