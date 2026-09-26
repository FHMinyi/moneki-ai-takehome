"""Diagnosis only: real starter paths, temporary fixtures, no production fixes.
Run with PYTHONPATH=<isolated source>/starter G2_SOURCE=<isolated source>.
"""
import os,json,subprocess,shutil
from pathlib import Path
from datetime import date
import pytest
from kbqa.loader import load_knowledge_base,load_document,Document
from kbqa.chunker import chunk_document,Chunk
from kbqa.index import load_index,BM25Index
from kbqa.aliases import AliasTable
from kbqa.retriever import Retriever
from kbqa.tokenizer import tokenize
ROOT=Path(os.environ['G2_SOURCE'])
KB=ROOT/'knowledge_base'
TODAY=date(2026,9,1)
@pytest.fixture(scope='module')
def idx(tmp_path_factory):
    return load_index(KB,tmp_path_factory.mktemp('index')/'index.json')

def test_formats_all_document_ids_enter_index(idx):
    expected={p.name.split('_')[0] for p in KB.rglob('KB-*') if p.is_file()}
    assert set(idx.docs_meta)==expected, {'missing':sorted(expected-set(idx.docs_meta))}

def test_real_gbk_document_preserves_visible_words():
    path=next(KB.rglob('KB-062*'))
    original=path.read_bytes().decode('gbk')
    assert '营业时间' in original
    actual=load_document(path).text
    assert '营业时间' in actual and '周五' in actual, actual[:160]

def test_real_html_excludes_scripts_styles_and_tags():
    doc=load_document(next(KB.rglob('KB-061*')))
    assert '小程序' in doc.text
    assert '<script' not in doc.text and 'window.dataLayer' not in doc.text and '<style' not in doc.text

@pytest.mark.parametrize('size',[300,301,600,601])
def test_chunking_keeps_last_character(size):
    body='甲'*(size-1)+'尾'
    doc=Document('KB-900','diagnostic',body,Path('KB-900.md'),'md')
    pieces=chunk_document(doc)
    assert ''.join(c.source_text for c in pieces)==body, {'input':size,'retained':sum(len(c.source_text) for c in pieces)}

def test_chinese_query_gets_positive_relevant_score():
    doc=Document('KB-900','退款','外卖订单在送达后24小时内可以申请退款。',Path('KB-900.md'),'md')
    index=BM25Index(chunk_document(doc),{doc.doc_id:doc.meta()},AliasTable(),'test')
    terms=tokenize('外卖订单多久内可以申请退款')
    scores=index.score_terms({term:1.0 for term in terms})
    assert scores, {'terms':terms,'document_terms':tokenize(doc.text)}

def test_returned_doc_id_matches_real_chunk_owner(idx):
    result=Retriever(idx,TODAY).search('S04 为什么不卖吞拿鱼三明治了',5)
    owners={c.chunk_id:c.doc_id for c in idx.chunks}
    mismatches=[{'doc_id':h.doc_id,'chunk_id':h.chunk_id,'owner':owners[h.chunk_id]} for h in result.hits if h.doc_id!=owners[h.chunk_id]]
    assert not mismatches,mismatches

def test_current_policy_excludes_superseded_version(idx):
    r=Retriever(idx,TODAY)
    assert idx.docs_meta['KB-012']['superseded_by']=='KB-013'
    assert r._eligible('KB-012',TODAY,None) is not None,idx.docs_meta['KB-012']

def test_filter_before_topk_retains_available_matching_result():
    chunks=[Chunk('KB-901','KB-901#1','refund','refund'),Chunk('KB-902','KB-902#1','refund filler','refund filler')]
    meta={'KB-901':{'stores_explicit':True,'stores':['S01']},'KB-902':{'stores_explicit':True,'stores':['S02']}}
    r=Retriever(BM25Index(chunks,meta,AliasTable(),'test'),TODAY)
    result=r.search('refund',1,store_id='S02')
    assert len(result.hits)==1 and result.hits[0].doc_id=='KB-902',result.as_trace()

@pytest.mark.parametrize('change',['add','modify','delete','switch_directory'])
def test_cache_reflects_knowledge_base_change(tmp_path,change):
    kb=tmp_path/'kb';kb.mkdir(); cache=tmp_path/'index.json'
    p=kb/'KB-900.md';p.write_text('# Original\noriginal sentinel',encoding='utf8')
    first=load_index(kb,cache)
    if change=='add':(kb/'KB-901.md').write_text('# Added\nnew sentinel',encoding='utf8')
    elif change=='modify':p.write_text('# Changed\nchanged sentinel',encoding='utf8')
    elif change=='delete':p.unlink()
    else:
        kb=tmp_path/'other';kb.mkdir();(kb/'KB-902.md').write_text('# Other\nother sentinel',encoding='utf8')
    observed=load_index(kb,cache)
    fresh=load_index(kb,tmp_path/'fresh.json')
    assert observed.texts==fresh.texts, {'cached':observed.texts,'fresh':fresh.texts,'same_key':first.key==fresh.key}

def test_health_reports_actual_indexed_documents():
    from kbqa.config import load_settings
    from kbqa.service import Service
    service=Service(load_settings())
    assert service.health()['kb_docs']==len(service.index.docs_meta),{'reported':service.health()['kb_docs'],'indexed':len(service.index.docs_meta)}

def test_public_rebuild_command_detects_added_document(tmp_path):
    # Copy only source code; never reuse the checkout cache and never mutate original KB.
    source=tmp_path/'starter';source.mkdir()
    shutil.copytree(ROOT/'starter/kbqa',source/'kbqa',ignore=shutil.ignore_patterns('__pycache__'))
    kb=tmp_path/'kb';kb.mkdir();(kb/'KB-900.md').write_text('# First\nfirst',encoding='utf8')
    env=os.environ.copy()
    env.update(PYTHONPATH=str(source),KB_DIR=str(kb),DATA_DIR=str(ROOT/'data'),VAR_DIR=str(tmp_path/'var'))
    for key in ('LLM_API_KEY','LLM_BASE_URL','LLM_MODEL'):env.pop(key,None)
    args=[os.sys.executable,'-m','kbqa.rebuild']
    first=subprocess.run(args,cwd=source,env=env,capture_output=True,text=True)
    assert first.returncode==0,first.stdout+first.stderr
    (kb/'KB-901.md').write_text('# Added\nnew sentinel',encoding='utf8')
    second=subprocess.run(args,cwd=source,env=env,capture_output=True,text=True)
    assert second.returncode==0,second.stdout+second.stderr
    cached=json.loads((source/'.cache/index.json').read_text())
    assert 'KB-901' in cached['docs'],second.stdout

def test_control_ascii_query_has_positive_score():
    c=Chunk('KB-900','KB-900#1','refund policy','refund policy')
    idx=BM25Index([c],{'KB-900':{}},AliasTable(),'test')
    assert idx.score_terms({'refund':1.0})

def test_control_historical_old_policy_is_available(idx):
    assert Retriever(idx,TODAY)._eligible('KB-012',date(2026,6,1),None) is None
