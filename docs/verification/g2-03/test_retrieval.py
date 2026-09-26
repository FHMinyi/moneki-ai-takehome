"""Real rebuilt index and HTTP; independent of starter's fixed Retriever fixture."""
from contextlib import contextmanager
from datetime import date
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'starter'))
spec = importlib.util.spec_from_file_location('g2_ingestion_runtime', ROOT / 'docs/verification/g2-01/test_ingestion.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from kbqa.index import load_index
from kbqa.retriever import Retriever

class Runtime(module.Runtime):
    @contextmanager
    def serve(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        cmd = [sys.executable, '-m', 'uvicorn', 'kbqa.server:app', '--host', '127.0.0.1', '--port', str(port)]
        with (self.root / 'server.log').open('a') as log:
            p = subprocess.Popen(cmd, cwd=self.source, env=self.env, stdout=log, stderr=log)
            record = dict(command=cmd, pid=p.pid, port=port, requests=[])
            self.records.append(record)
            def request(path, body=None):
                req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=json.dumps(body).encode() if body is not None else None, headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req, timeout=20) as response:
                    result = json.load(response)
                record['requests'].append(dict(path=path, body=body, response=result))
                return result
            try:
                for _ in range(200):
                    try:
                        health = request('/api/health')
                        break
                    except OSError:
                        assert p.poll() is None, (self.root/'server.log').read_text()
                        time.sleep(.05)
                else:
                    raise AssertionError('startup timeout')
                assert health['llm_mode'] == 'mock'
                yield request
            finally:
                p.terminate()
                p.wait(timeout=10)
                record['stopped'] = p.poll() is not None

@pytest.fixture
def rt(tmp_path, request):
    runtime = Runtime(tmp_path, request.node.name)
    yield runtime
    if os.environ.get('G2_EVIDENCE'):
        out = Path(os.environ['G2_EVIDENCE'])
        out.mkdir(parents=True, exist_ok=True)
        (out/(request.node.name+'.json')).write_text(json.dumps(dict(source=str(runtime.source),records=runtime.records),ensure_ascii=False,indent=2))

def original(rt):
    shutil.copytree(ROOT/'knowledge_base', rt.kb, dirs_exist_ok=True)
    return rt.build()

def get(request, query, k=5):
    return request('/api/retrieve', dict(query=query, top_k=k))

def evidence(response):
    return [h for h in response['results'] if h['score'] > 0 and not h.get('padded',False)]

def write(rt, num, text, meta=''):
    (rt.kb/f'KB-{num}.md').write_text('---\n'+meta+'\n---\n'+text)

PUBLIC = [json.loads(line) for line in (ROOT/'eval/public_questions.jsonl').read_text().splitlines() if json.loads(line)['category']=='retrieval']

@pytest.mark.parametrize('q', PUBLIC, ids=lambda q:q['id'])
def test_public_positive(rt,q):
    payload = original(rt)
    with rt.serve() as request:
        response=get(request,q['query'],q['top_k'])
    hits=response['results']
    assert len(hits)==q['results_count']
    assert [h['score'] for h in hits]==sorted([h['score'] for h in hits],reverse=True)
    ids={h['doc_id'] for h in evidence(response)}
    assert set(q.get('gold_all',[]))<=ids
    assert not q.get('gold_any') or set(q['gold_any'])&ids
    chunks={c['chunk_id']:c for c in payload['chunks']}
    for h in hits:
        c=chunks[h['chunk_id']]
        assert h['doc_id']==c['doc_id'] and h['text']==c['source_text']

VARIANTS=[
 ('请说明外卖退款的申请时限','KB-013','退款'),
 ('员工买餐折扣能与促销叠加吗','KB-014','折'),
 ('Beef Poke里面有哪些过敏原？','KB-040','牛肉'),
 ('Ｂｅｅｆ　Ｐｏｋｅ：过敏原？','KB-040','牛肉'),
 ('吞拿鱼三明治在Ｓ０４停售的原因','KB-029','三明治'),
 ('阿里嘎多的吞拿鱼三明治为何停售','KB-029','三明治'),
 ('汤面店周五几点关门','KB-062','周五'),
 ('S01周五几点关门','KB-062','周五'),
 ('开具电子发票的操作流程','KB-061','发票'),
 ('台风导致提前闭店的具体时间','KB-026','闭店'),
]
@pytest.mark.parametrize('query,gold,support', VARIANTS)
def test_variants(rt,query,gold,support):
    original(rt)
    with rt.serve() as request:
        hits=evidence(get(request,query))
    assert any(h['doc_id']==gold and support in h['retrieval_text'] for h in hits),hits

@pytest.mark.parametrize('query,gold,excluded',[
 ('现在外卖退款的政策规定','KB-013','KB-012'),
 ('2026-06-14当时的外卖退款规定','KB-012','KB-013'),
 ('2026-06-15当时的外卖退款规定','KB-013','KB-012'),
])
def test_real_versions(rt,query,gold,excluded):
    original(rt)
    with rt.serve() as request:
        r=get(request,query)
    ids={h['doc_id'] for h in evidence(r)}
    assert gold in ids and excluded not in ids, r

@pytest.mark.parametrize('query,gold',[
 ('现在refundtoken退款规定','KB-902'),
 ('2026-05-31当时refundtoken退款规定','KB-901'),
 ('2026-06-01当时refundtoken退款规定','KB-902'),
])
def test_version_boundaries(rt,query,gold):
    write(rt,901,'refundtoken退款申请限时9小时。','status: 已被取代\neffective_from: 2026-01-01\nsuperseded_by: KB-902')
    write(rt,902,'refundtoken退款申请限时7小时。','status: 现行\neffective_from: 2026-06-01')
    payload=rt.build()
    with rt.serve() as request:
        r=get(request,query,5)
    assert len(r['results'])==len(payload['chunks'])
    assert {h['doc_id'] for h in evidence(r)}=={gold}, r
    assert all(h.get('padded') and h.get('exclusion_reason') and h['score']==0 for h in r['results'] if h['doc_id']!=gold)
    assert all('status' in m for m in payload['docs'].values())

@pytest.mark.parametrize('k',[1,2,5,100])
def test_filter_before_topk_and_padding(rt,k):
    write(rt,901,'cooltoken cooltoken refrigeration规定4度。','stores: [S01]')
    write(rt,902,'cooltoken refrigeration规定8度。','stores: [S02]')
    payload=rt.build()
    with rt.serve() as request:
        r=get(request,'S02 cooltoken refrigeration规定',k)
        chat=request('/api/chat',dict(session_id='scope',question='S02 cooltoken refrigeration规定'))
        trace=request('/api/trace/'+chat['trace_id'])
    assert len(r['results'])==min(k,len(payload['chunks']))
    assert {h['doc_id'] for h in evidence(r)}=={'KB-902'},r
    assert all(c['doc_id']!='KB-901' for c in chat['citations']),chat
    searches=[s['detail'] for s in trace['steps'] if s['step']=='search']
    assert searches,trace
    assert all(h['padded'] for h in searches[0]['hits'] if h['doc_id']=='KB-901')


def test_incidental_store_is_not_scope(rt):
    write(rt,901,'sharedtoken 通用制度，正文以 S01 举例，所有门店均应遵守。')
    rt.build()
    with rt.serve() as request:
        r=get(request,'S02 sharedtoken 通用制度',1)
    assert {h['doc_id'] for h in evidence(r)}=={'KB-901'}


def test_unknown_and_padding_chat(rt):
    write(rt,901,'cobaltsecret 规章规定领取17枚硬币。','stores: [S01]')
    rt.build()
    with rt.serve() as request:
        r=get(request,'S02 cobaltsecret规章规定',5)
        chat=request('/api/chat',dict(session_id='none',question='S02 cobaltsecret规章规定'))
        unknown=get(request,'zzzxylophoneqqq')
    assert not evidence(r),r
    assert not chat['citations'] and chat['answer_type']=='refusal',chat
    assert not evidence(unknown)
    assert unknown['diagnostics']['coverage']==0


def test_same_search_http_and_trace(rt):
    original(rt)
    with rt.serve() as request:
        q='2026-06-14当时的外卖退款政策规定'
        r=get(request,q)
        chat=request('/api/chat',dict(session_id='same',question=q))
        trace=request('/api/trace/'+chat['trace_id'])
    searches=[s['detail'] for s in trace['steps'] if s['step']=='search']
    assert searches,trace
    assert r['diagnostics']['terms']
    assert r['diagnostics']['filtered']
    assert r['diagnostics']['candidates']
    assert r['diagnostics']['hits']==searches[0]['hits']
    assert r['diagnostics']['terms']==searches[0]['terms']


def test_replacement_alias_and_fact(rt):
    for alias,fact in [('Azure Bowl','17'),('Violet Plate','23')]:
        write(rt,970,'| 标准写法 | alias |\n|---|---|\n| 翡翠饭 | '+alias+' |')
        write(rt,971,'翡翠饭的配送时限为'+fact+'分钟。')
        rt.build()
        with rt.serve() as request:
            r=get(request,alias+'的配送时限规定')
            old=get(request,'Azure Bowl' if alias=='Violet Plate' else 'zzzxylophoneqqq')
        assert any(h['doc_id']=='KB-971' and fact in h['text'] for h in evidence(r)),r
        if alias=='Violet Plate':
            assert not evidence(old),old

@pytest.mark.parametrize('query,gold,required',[
 ('三文鱼那次断供供应商赔了多少钱','KB-022','CNY'),
 ('S04 为什么不卖吞拿鱼三明治了','KB-029','低于'),
])
def test_gold_chunk_contains_support_not_only_heading(rt,query,gold,required):
    original(rt)
    with rt.serve() as request:
        r=get(request,query)
    assert any(h['doc_id']==gold and required in h['text'] for h in evidence(r)),r

@pytest.mark.parametrize('q',[
 '2026年6月14日当时的外卖退款政策规定',
 '２０２６／０６／１４当时的外卖退款政策规定',
 '现在S02的退款政策规定',
])
def test_rewritten_chat_search_is_reproducible(rt,q):
    original(rt)
    with rt.serve() as request:
        chat=request('/api/chat',dict(session_id='rewritten',question=q))
        trace=request('/api/trace/'+chat['trace_id'])
        searches=[s['detail'] for s in trace['steps'] if s['step']=='search']
        assert searches,trace
        search=searches[0]
        direct=get(request,search['query'])
    assert direct['diagnostics']['hits']==search['hits']
    assert direct['diagnostics']['scope']==search['scope']
    if '14' in q or '１４' in q:
        assert search['scope']['as_of']=='2026-06-14'


def test_actual_store_scope_and_incidental_examples(rt):
    original(rt)
    with rt.serve() as request:
        r=get(request,'S02排烟管道整改停业通知',50)
        incidental=get(request,'S02净营业额退款口径',5)
    assert 'KB-020' not in {h['doc_id'] for h in evidence(r)}
    assert any(f['doc_id']=='KB-020' and 'S03' in f['reason'] for f in r['diagnostics']['filtered'])
    assert 'KB-001' in {h['doc_id'] for h in evidence(incidental)}


def test_tool_uses_only_eligible_evidence(rt):
    write(rt,901,'cobaltsecret 规章规定领取17枚硬币。','stores: [S01]')
    rt.build()
    script='''import json
from kbqa.service import Service
s=Service()
print(json.dumps({'api':s.retrieve('S02 cobaltsecret规章规定'), 'tool':s.run_tool('search_kb',{'query':'S02 cobaltsecret规章规定'})},ensure_ascii=False))
'''
    p=subprocess.run([sys.executable,'-c',script],cwd=rt.source,env=rt.env,text=True,capture_output=True)
    assert p.returncode==0,p.stderr
    value=json.loads(p.stdout)
    rt.records.append(dict(command=[sys.executable,'-c',script],result=value))
    assert value['api']['results'] and not value['tool']['results']


def test_unknown_chinese_keeps_low_coverage(rt):
    payload=original(rt)
    with rt.serve() as request:
        r=get(request,'量子纠缠宇宙飞船跃迁引擎规定')
        empty=get(request,'？！',500)
    assert r['diagnostics']['coverage']<.25
    assert not evidence(empty) and empty['diagnostics']['coverage']==0
    assert len(empty['results'])==len(payload['chunks'])

@pytest.mark.parametrize('q,gold,word',[
 ('鲑鱼波奇饭断供的赔付金额是多少','KB-022','CNY'),
 ('阿里嘎多下架金枪鱼三明治是什么原因','KB-029','低于'),
])
def test_supported_variants(rt,q,gold,word):
    original(rt)
    with rt.serve() as request:
        r=get(request,q)
    assert any(h['doc_id']==gold and word in h['text'] for h in evidence(r)),r


def test_shape_rerank_replacement_and_no_lexical_match(rt):
    for alias,amount in [('Jade Trout','4321'),('Amber Cod','6789')]:
        write(rt,980,'| 标准写法 | alias |\n|---|---|\n| 星河鱼 | '+alias+' |')
        write(rt,981,'# '+alias+' delivery\n\n1. DETAILS\n\n'+('The shipment was delayed. '*18)+'\n\n2. SETTLEMENT\n\nCredit issued: CNY '+amount+'.\n')
        payload=rt.build()
        with rt.serve() as request:
            r=get(request,'星河鱼供应商赔付金额是多少')
            unknown=get(request,'zzzxylophoneqqq金额多少钱')
        assert any(h['doc_id']=='KB-981' and amount in h['text'] for h in evidence(r)),r
        # Fact shape alone (CNY) must never create a lexical candidate.
        assert not evidence(unknown),unknown
        assert unknown['diagnostics']['candidates']==[]
        if alias=='Amber Cod':
            assert '4321' not in json.dumps(payload) and 'Jade Trout' not in json.dumps(payload)
