"""Single store, one day, two actual receipt prices: trace follows query scope."""
import importlib.util,json,sys,sqlite3
from pathlib import Path
from test_replay import ROOT
from kbqa.document_evidence import DocumentEvidence
from kbqa.mixed_answer import render_mixed
from kbqa.trace import Trace
spec=importlib.util.spec_from_file_location('old_mixed_fixtures',ROOT/'docs/verification/g3-03/test_mixed.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)

def test_single_store_multiple_actual_prices_trace(tmp_path):
 service=old.independent_service(tmp_path)
 con=sqlite3.connect(service.settings.source_db)
 con.execute('INSERT INTO sales VALUES(?,?,?,?,?,?,?)',('SECOND-PRICE','2026-06-18','S02','P06','1','34.50','现金'));con.commit();con.close()
 (service.settings.kb_dir/'KB-991.md').write_text('---\ntitle: 牛肉poke价格通知\neffective_from: 2026-06-18\nstores: [S02]\n---\n牛肉poke售价34.50元。')
 service.tools.close();service.rebuild()
 plan=service.planner.plan('6月18日S02牛肉poke多少钱一份？')
 params=dict(product_id='P06',start='2026-06-18',end='2026-06-18',store_id='S02')
 result=service.run_tool('unit_price_check',params)
 assert result['by_store']=={'S02':{'30.00':1,'34.50':1}}
 pool=DocumentEvidence(service.facts);pool.add(service.run_tool('search_kb',dict(query='牛肉poke售价'),plan=plan)['evidence'])
 price=next(e for e in pool.items.values() if e['doc_id']=='KB-991' and '34.50' in e['quote'])
 payload=dict(answer_type='hybrid',mode='price',results=[dict(call_id='db',metric='unit_price')],facts=[dict(evidence_id=price['evidence_id'],role='price')])
 trace=Trace('single-store','q')
 a=render_mixed(payload,[dict(_call_id='db',tool='unit_price_check',params=params,result=result)],pool,plan,service.catalog,trace,search_performed=True)
 assert a.answer_type=='hybrid' and 'S02 实收单价 30.00、34.50 元' in a.answer
 assert a.data_evidence[0]['calculations'][0]['result']==-7.5
 binding=next(s for s in trace.steps if s['step']=='mixed_binding')['detail']['bindings'][0]
 assert binding['query_stores']=='S02',binding
