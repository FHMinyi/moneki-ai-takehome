"""Free original-response replay through Service + real tools; no network allowed."""
from evidence_io import read_jsonl
import json,sys,tempfile,os
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import httpx
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'starter'))
from kbqa.config import load_settings
from kbqa.service import Service
from kbqa.llm import LLMClient

DOC_CHATS={7:'C01',8:'C02',9:'C03',10:'C04',12:'C06',14:'C08',16:'V02',17:'V03-1',29:'T02-2',37:'S01'}
LENGTH_CHATS={11:'C05',15:'V01',30:'T02-3'}

def run(output):
 rows=read_jsonl(HERE/'chat-trace.jsonl')
 traffic=read_jsonl(HERE/'model-traffic.jsonl')
 service=Service(replace(load_settings(),var_dir=Path(tempfile.mkdtemp(prefix='g302-live-replay-')),
   llm_api_key='offline-replay-only',llm_base_url='http://network-is-forbidden.invalid',llm_model='deepseek-flash'))
 per_chat={}
 for r in traffic:per_chat.setdefault(r['chat'],[]).append(r)
 original_traces={r['chat']:r['response'] for r in rows if r['path'].startswith('/api/trace/')}
 results=[];failures=[]
 for record in rows:
  if record['path']!='/api/chat':continue
  n=record['chat'];queue=list(per_chat.get(n,[]));calls=[]
  def post(self,body,timeout):
   assert queue,'Replay may not generate new provider responses'
   entry=queue.pop(0);calls.append(entry['attempt'])
   return httpx.Response(entry['status'],content=entry['response'].encode(),headers={'Content-Type':'application/json'})
  with patch.object(LLMClient,'_post',post):
   q=record['request'];actual=service.chat(q.get('session_id'),q['question'],q.get('context'))
  trace=service.get_trace(actual['trace_id'])
  result={'chat':n,'case':DOC_CHATS.get(n,LENGTH_CHATS.get(n)), 'execution':'free saved provider responses; real local tools; no new model call',
    'request':q,'original_response':record['response'],'response':actual,'trace':trace,'replayed_attempts':calls,'unused_original_attempts':len(queue)}
  results.append(result)
  reasons=[s['detail'].get('reason') for s in trace['steps'] if s['step']=='document_binding_rejected']
  errors=[e.get('message') for e in trace['errors']]
  if n in DOC_CHATS:
   if actual['answer_type']!='doc':failures.append(DOC_CHATS[n])
   print(n,DOC_CHATS[n],actual['answer_type'],reasons,errors)
  elif n in LENGTH_CHATS:print(n,LENGTH_CHATS[n],actual['answer_type'],errors)
 output=Path(output);assert not output.exists(),'Use a fresh output path';output.parent.mkdir(parents=True,exist_ok=True)
 output.write_text(json.dumps({'base':'4591fab9a80ef63c440b9a117dbbc4fcbf03c430','results':results,'document_cases_not_answered':failures},ensure_ascii=False,indent=2))
 print('document failures',len(failures),failures)
 return len(failures)
if __name__=='__main__':sys.exit(bool(run(sys.argv[1])))
