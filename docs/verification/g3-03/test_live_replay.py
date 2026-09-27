"""Replay saved provider choices free; not a new real-model semantic trial."""
import json, os, tempfile
from pathlib import Path
from test_mixed import service, QUESTIONS
from kbqa.document_evidence import DocumentEvidence
from kbqa.mixed_answer import render_mixed
from kbqa.trace import Trace

def test_real_h01_selection_filter_preserves_dated_event(service):
 p=json.loads((Path(__file__).parent/'live/chat-2.json').read_text())
 pool=DocumentEvidence(service.facts);evidence=[]
 for s in p['trace']['steps']:
  if s['step']=='document_evidence':pool.add(s['detail']['evidence'])
  if s['step']=='tool' and s['detail']['tool']!='search_kb':
   d=s['detail'];evidence.append(dict(_call_id=d['call_id'],tool=d['tool'],params=d['params'],result=d['result']))
 payload=json.loads(p['trace']['llm_calls'][-1]['response']['choices'][0]['message']['content'])
 trace=Trace('g303-free-replay',QUESTIONS['H01'])
 a=render_mixed(payload,evidence,pool,service.planner.plan(QUESTIONS['H01']),service.catalog,trace,search_performed=True)
 assert a.answer_type=='hybrid' and '3630.00' in a.answer and '停业' in a.answer
 assert len(a.citations)==1 and '2026-06-05' not in a.answer
 assert any(s['step']=='mixed_evidence_filtered' for s in trace.steps)
 (Path(os.environ.get('G303_REPLAY_OUT',tempfile.mkdtemp(prefix='g303-replay-')))/'replay-chat-2.json').write_text(json.dumps(dict(response=a.__dict__,steps=trace.steps,mode='FREE_REPLAY_NOT_NEW_PROVIDER_CALL'),ensure_ascii=False,indent=2))

def test_real_payment_selection_preserves_model_selected_source(service):
 p=json.loads((Path(__file__).parent/'live/chat-3.json').read_text())
 pool=DocumentEvidence(service.facts);ev=[]
 for s in p['trace']['steps']:
  if s['step']=='document_evidence':pool.add(s['detail']['evidence'])
  if s['step']=='tool' and s['detail']['tool']!='search_kb':
   d=s['detail'];ev.append(dict(_call_id=d['call_id'],tool=d['tool'],params=d['params'],result=d['result']))
 payload=json.loads(p['trace']['llm_calls'][-1]['response']['choices'][0]['message']['content'])
 trace=Trace('g303-free-replay-payment',QUESTIONS['H05'])
 a=render_mixed(payload,ev,pool,service.planner.plan(QUESTIONS['H05']),service.catalog,trace,search_performed=True)
 assert a.answer_type=='hybrid' and '100.00%' in a.answer
 # Updated contract delegates relevance to this same model selection.
 assert len(a.citations)==3 and '交换机升级' in a.answer
 assert '未据此估算' in a.answer
 assert all(c['quote']==pool.items[c['evidence_id']]['quote'] for c in a.citations)
 assert a.data_evidence[0]['calculations'][0]['numerator']==27
 (Path(os.environ.get('G303_REPLAY_OUT',tempfile.mkdtemp(prefix='g303-replay-')))/'replay-chat-3.json').write_text(json.dumps(dict(response=a.__dict__,steps=trace.steps,mode='FREE_REPLAY_NOT_NEW_PROVIDER_CALL'),ensure_ascii=False,indent=2))
