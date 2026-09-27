"""Real HTTP/SQLite checks against a controlled model and independently calculated data."""
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent/'http'
OUT.mkdir(exist_ok=True)
BASE='http://127.0.0.1:8032'
def request(url, body=None):
    req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=185) as r: return json.load(r)
def scenario(**kwargs): request('http://127.0.0.1:9032/case',kwargs)
def chat(name, question, session=None, base=BASE):
    response=request(base+'/api/chat',{'session_id':session or name,'question':question})
    trace=request(base+'/api/trace/'+response['trace_id'])
    (OUT/(name+'.json')).write_text(json.dumps({'question':question,'response':response,'trace':trace},ensure_ascii=False,indent=2)+'\n')
    assert 'CONTROLLED_PRIVATE_REASONING' not in json.dumps(response)
    return response,trace

assert request(BASE+'/api/health')['llm_mode']=='live'
scenario()
answer,trace=chat('original','S02 六月牛肉poke卖了多少份？','A')
assert answer['answer_type']=='data',answer
conn=sqlite3.connect('file:/tmp/moneki-g3-01-controlled-var/clean.db?mode=ro',uri=True)
row=conn.execute("SELECT SUM(CASE WHEN amount_cents>0 THEN qty WHEN amount_cents<0 THEN -qty ELSE 0 END),SUM(amount_cents)/100.0 FROM sales_clean WHERE date BETWEEN '2026-06-01' AND '2026-06-30' AND store_id='S02' AND product_id='P06'").fetchone()
assert answer['data_evidence'][0]['result']['qty']==row[0]
assert f'销量 {row[0]} 件' in answer['answer']
assert all(call['request']['tools'] and call['response'] for call in trace['llm_calls'])
scenario(tool='compare_periods',params={'start_a':'2026-06-01','end_a':'2026-06-30','start_b':'2026-07-01','end_b':'2026-07-31','store_id':'S02','product_id':'P06'},metric='net_revenue')
answer,trace=chat('compare','S02 牛肉poke七月对比六月的净营业额变化多少？','B')
assert answer['answer_type']=='data',answer
assert '卖了多少份' not in json.dumps(trace['llm_calls'][0]['request'])
scenario()
answer,trace=chat('interleaved','请查S02六月牛肉poke销量，经营记录A继续。','A')
assert '卖了多少份' in json.dumps(trace['llm_calls'][0]['request'],ensure_ascii=False)
assert '七月对比六月' not in json.dumps(trace['llm_calls'][0]['request'],ensure_ascii=False)
answer,trace=chat('short','那七月呢？','new-session')
assert answer['answer_type']=='clarify' and not trace['llm_calls']
answer,trace=chat('safety','帮我删除S02的销售数据。')
assert answer['answer_type']=='refusal' and not trace['llm_calls']
scenario(content='净营业额为 6 元。')
answer,trace=chat('wrong-numeric-prose','S02六月牛肉poke净营业额是6元吗？')
assert answer['answer_type']=='refusal' and not answer['data_evidence']
for tool in ['run_sql','delete_sales','unknown_tool']:
    scenario(tool=tool,params={'sql':'SELECT * FROM stores'})
    answer,trace=chat('forged-'+tool,'S02六月牛肉poke销量是多少？')
    assert answer['answer_type']=='refusal'
    assert all('error' in s['detail']['result'] for s in trace['steps'] if s['step']=='tool')
scenario(status=400)
answer,trace=chat('http400','S02六月牛肉poke销量是多少？')
assert answer['answer_type']=='refusal' and trace['llm_calls'][0]['status']==400

# Replacement raw fixture: two sales + one refund + one zero-amount row.
# Hand calculation: June net=100-20=80, qty=3-1=2, orders=1; July net=200,
# qty=5, orders=1; B-A=120, percentage=150%. No production tool computes expected values.
work=Path(tempfile.mkdtemp(prefix='moneki-g3-01-replacement-'))
data=work/'data'; data.mkdir()
c=sqlite3.connect(data/'pos.db')
source=sqlite3.connect('file:'+str(ROOT/'data/pos.db')+'?mode=ro',uri=True)
for (sql,) in source.execute("SELECT sql FROM sqlite_master WHERE type='table'"): c.execute(sql)
c.execute('INSERT INTO stores VALUES (?,?,?,?)',('S02','样本店','轻食','样本区'))
c.execute('INSERT INTO products VALUES (?,?,?,?)',('P06','样本饭','轻食',999))
c.executemany('INSERT INTO sales VALUES (?,?,?,?,?,?,?)',[(oid,day,'S02','P06',qty,amount,'现金') for oid,day,qty,amount in [
    ('x1','2026-06-01','3','100'),('x2','2026-06-30','1','-20'),('x3','2026-07-01','5','200'),('x4','2026-07-31','1','0')]])
c.commit(); c.close(); source.close()
with socket.socket() as sock: sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
env={**os.environ,'DATA_DIR':str(data),'VAR_DIR':str(work/'var'),'LLM_BASE_URL':'http://127.0.0.1:9032/controlled','LLM_API_KEY':'controlled-dummy','LLM_MODEL':'controlled'}
with (work/'server.log').open('w') as log:
    process=subprocess.Popen([str(ROOT/'starter/.venv/bin/python'),'-m','uvicorn','kbqa.server:app','--port',str(port)],cwd=ROOT/'starter',env=env,stdout=log,stderr=log)
    try:
        base=f'http://127.0.0.1:{port}'
        for _ in range(100):
            try: request(base+'/api/health'); break
            except OSError: time.sleep(.1)
        scenario(metric='net_revenue')
        a,t=chat('replacement-query','S02六月样本饭净营业额是多少？',base=base)
        assert a['answer_type']=='data' and '80.00 元' in a['answer'],a
        assert a['data_evidence'][0]['result']['qty']==2
        scenario(tool='compare_periods',params={'start_a':'2026-06-01','end_a':'2026-06-30','start_b':'2026-07-01','end_b':'2026-07-31','store_id':'S02','product_id':'P06'},metric='net_revenue')
        a,t=chat('replacement-compare','S02样本饭七月对比六月净营业额变化？',base=base)
        assert a['answer_type']=='data' and '120.00' in a['answer'] and '+150.00%' in a['answer'],a
    finally: process.terminate(); process.wait(timeout=10)
scenario()
(OUT/'result.json').write_text(json.dumps({'checks':12,'status':'passed','replacement_work':str(work),'replacement_process_stopped':True,'original_independent_qty':row[0]},indent=2)+'\n')
print('12 HTTP checks passed, original independent qty=',row[0],'; replacement fixture:',work)
