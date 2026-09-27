"""Replay immutable original model content at the document finalisation boundary.
No provider call, ID rewriting, prompt replacement, or changed source evidence.
This is not a fresh retrieval or end-to-end model evaluation.
"""
from evidence_io import read_jsonl
import json,sys,tempfile
from pathlib import Path
from dataclasses import replace,asdict
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'starter'))
from kbqa.config import load_settings
from kbqa.service import Service
from kbqa.document_evidence import DocumentEvidence
from kbqa.trace import Trace
from kbqa.llm import LLMClient
from unittest.mock import patch
from replay import DOC_CHATS

def run(output):
 rows=read_jsonl(HERE/'chat-trace.jsonl')
 traffic=read_jsonl(HERE/'model-traffic.jsonl')
 service=Service(replace(load_settings(),var_dir=Path(tempfile.mkdtemp(prefix='g302-finalise-'))))
 results=[]
 for n,case in DOC_CHATS.items():
  original=next(r['response'] for r in rows if r['chat']==n and r['path'].startswith('/api/trace/'))
  plan=next(s['detail'] for s in original['steps'] if s['step']=='plan')
  pool=DocumentEvidence(service.facts)
  validated=0
  for step in original['steps']:
   if step['step']!='document_evidence':continue
   for item in step['detail']['evidence']:
    source=service.facts.index.texts[item['doc_id']]
    for span in [item,*item['context']]:
     assert source[span['source_start']:span['source_end']]==span['quote'],(case,item['evidence_id'],'source drift')
    validated+=1
   pool.add(step['detail']['evidence'])
  finals=[]
  for entry in traffic:
   if entry['chat']!=n or entry['status']!=200:continue
   response=json.loads(entry['response'])
   choice=response['choices'][0]
   if choice['finish_reason']=='stop' and choice['message'].get('content'):
    finals.append((entry['attempt'],choice['message']['content']))
  attempt,content=finals[-1]
  trace=Trace('offline-'+case,plan['standalone_question'])
  with patch.object(LLMClient,'_post',side_effect=AssertionError('Network forbidden')):
   try:
    answer=pool.render(content,plan['standalone_question'],trace)
    result={'answer_type':answer.answer_type,'answer':answer.answer,'citations':answer.citations}
   except Exception as exc:result={'answer_type':'error','exception':type(exc).__name__,'message':str(exc)}
  reasons=[s['detail']['reason'] for s in trace.steps if s['step']=='document_binding_rejected']
  original_reasons=[s['detail']['reason'] for s in original['steps'] if s['step']=='document_binding_rejected']
  results.append(dict(case=case,chat=n,attempt=attempt,question=plan['standalone_question'],original_reasons=original_reasons,reasons=reasons,validated_spans=validated,content=content,result=result,steps=trace.steps))
  print(case,result['answer_type'],reasons,'original',original_reasons)
 path=Path(output);assert not path.exists();path.write_text(json.dumps({'boundary':'saved final model output + saved executor evidence; all source/context offsets validated against current KB; no retrieval or provider call','results':results},ensure_ascii=False,indent=2))
 return results
if __name__=='__main__':
 results=run(sys.argv[1]);sys.exit(any(r['result']['answer_type']!='doc' for r in results))
