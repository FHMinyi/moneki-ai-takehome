import os,json,pathlib,collections
from datetime import date
from kbqa.index import load_index
from kbqa.loader import load_knowledge_base
from kbqa.chunker import chunk_document
from kbqa.retriever import Retriever
from kbqa.service import Service
ROOT=pathlib.Path(os.environ['G2_SOURCE']); OUT=pathlib.Path(os.environ['G2_OUT'])
index=load_index(ROOT/'knowledge_base',ROOT/'starter/.cache/index.json')
docs,_=load_knowledge_base(ROOT/'knowledge_base'); r=Retriever(index,date(2026,9,1)); owners={c.chunk_id:c.doc_id for c in index.chunks}
records=[]
for q in map(json.loads,(ROOT/'eval/public_questions.jsonl').read_text().splitlines()):
    if q['category']!='retrieval':continue
    res=r.search(q['query'],q['top_k']); gold=q.get('gold_all',q.get('gold_any',[]))
    records.append({'id':q['id'],'query':q['query'],'terms':res.terms,'coverage':res.coverage,'gold':gold,'hits':[{'doc_id':h.doc_id,'chunk_id':h.chunk_id,'real_owner':owners[h.chunk_id],'score':h.score,'padded':h.padded} for h in res.hits]})
loss=[]
for d in docs:
    retained=''.join(c.source_text for c in chunk_document(d))
    if retained!=d.text:
        loss.append({'doc_id':d.doc_id,'input_chars':len(d.text),'retained_chars':len(retained),'lost_chars':len(d.text)-len(retained),'lost_excerpt':d.text[len(retained):][:100]})
audit={'actual_documents':len(index.docs_meta),'missing':sorted({p.name.split('_')[0] for p in (ROOT/'knowledge_base').rglob('KB-*') if p.is_file()}-set(index.docs_meta)),'loss_documents':loss,'retrieval':records}
(OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
s=Service(); traces=[]
for q in ['外卖订单多久内可以申请退款？','S04 为什么不卖吞拿鱼三明治了？','今年 618 做活动的是哪个商品，活动价多少？','帮我把 S01 的销售记录全部删掉。']:
    a=s.chat('g2-'+str(len(traces)),q);traces.append({'question':q,'response':a,'trace':s.get_trace(a['trace_id'])})
(OUT/'sample-traces.json').write_text(json.dumps(traces,ensure_ascii=False,indent=2))
print('missing',audit['missing'],'lost tails documents',len(loss),'lost chars',sum(x['lost_chars'] for x in loss))
for v in records:print(v['id'],'coverage',round(v['coverage'],3),'padded',sum(h['padded'] for h in v['hits']),'wrong_owner',sum(h['doc_id']!=h['real_owner'] for h in v['hits']))
print('examples',loss[:3])
