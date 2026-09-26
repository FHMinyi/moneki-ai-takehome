"""Real product regressions; never imports starter/tests/conftest.py."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import date

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'starter'))
from kbqa.chunker import CHUNK_SIZE, chunk_document
from kbqa.loader import Document, load_knowledge_base
from kbqa.index import build_index, load_index
from kbqa.docfacts import DocFacts

spec = importlib.util.spec_from_file_location('ingestion_runtime', ROOT / 'docs/verification/g2-01/test_ingestion.py')
ingestion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingestion)


@pytest.fixture
def runtime(tmp_path, request):
    rt = ingestion.Runtime(tmp_path, request.node.name)
    yield rt
    out = os.environ.get('G2_EVIDENCE')
    if out:
        path = Path(out)
        path.mkdir(parents=True, exist_ok=True)
        (path / (rt.name.replace('/', '_') + '.json')).write_text(json.dumps(
            dict(source=str(rt.source), records=rt.records), ensure_ascii=False, indent=2))


def coverage(doc, chunks):
    covered = set()
    for chunk in chunks:
        # Pre-fix implementation has no offsets; still expose actual lost characters.
        start = getattr(chunk, 'source_start', doc.text.find(chunk.source_text))
        end = getattr(chunk, 'source_end', start + len(chunk.source_text))
        assert start >= 0 and chunk.source_text == doc.text[start:end]
        covered.update(range(start, end))
    return len(doc.text) - len(covered)


@pytest.mark.parametrize('length', [0, 1, 299, 300, 301, 599, 600, 601, 900, 901])
def test_boundary_full_coverage(length):
    text = ''.join(chr(0x4e00 + i) for i in range(length))
    doc = Document('KB-901', 'metadata title', text, Path('KB-901.md'), 'md')
    assert coverage(doc, chunk_document(doc)) == 0


def test_actual_corpus_coverage(tmp_path):
    docs, _ = load_knowledge_base(ROOT / 'knowledge_base')
    audit = {d.doc_id: coverage(d, chunk_document(d)) for d in docs}
    if os.environ.get('G2_EVIDENCE'):
        out = Path(os.environ['G2_EVIDENCE']); out.mkdir(parents=True, exist_ok=True)
        (out / 'coverage.json').write_text(json.dumps(audit, indent=2))
    assert all(value == 0 for value in audit.values()), audit


def test_tail_fact_http(runtime):
    rt = runtime
    body = '# Procedure\n\n' + ('ordinary text ' * 80) + '\n\n尾段事实： tailtoken 关闭前核对温度 7 度。'
    (rt.kb / 'KB-901.md').write_text(body)
    payload = rt.build()
    health, responses = rt.http(['tailtoken'])
    assert health['kb_chunks'] == len(payload['chunks'])
    assert any(h['score'] > 0 and '关闭前核对温度 7 度' in h['text'] for h in responses['tailtoken']['results'])


def test_table_context_and_contiguous_quotes_http(runtime):
    rt = runtime
    rows = [f'| row{i:02} | {i} | 明细说明 |\n' for i in range(40)]
    rows[-1] = '| rowtoken | 77 | 最后一行事实 |\n'
    body = '# 调拨规则\n\n| Item | Count | Note |\n|---|---|---|\n' + ''.join(rows)
    (rt.kb / 'KB-901.md').write_text(body)
    payload = rt.build()
    _, responses = rt.http(['rowtoken'])
    hits = [h for h in responses['rowtoken']['results'] if h['score'] > 0 and '| rowtoken | 77 |' in h['text']]
    assert hits, responses
    index = load_index(rt.kb, rt.cache)
    chunk = next(c for c in index.chunks if c.chunk_id == hits[0]['chunk_id'])
    assert chunk.kind == 'table' and chunk.table_header == ['Item', 'Count', 'Note']
    assert '调拨规则' in chunk.heading and 'Count' in chunk.text
    assert chunk.source_text == body[chunk.source_start:chunk.source_end]
    assert chunk.source_text in body and chunk.text not in body
    assert chunk.context_spans
    for span in chunk.context_spans:
        assert span['text'] == body[span['start']:span['end']]
    assert hits[0]['text'] == chunk.source_text
    assert hits[0]['retrieval_text'] == chunk.text
    facts = DocFacts(index)
    assert facts.cite('KB-901', '| rowtoken | 77 | 最后一行事实 |')
    assert facts.cite('KB-901', chunk.text) is None


def test_offsets_context_and_cache_layout(runtime):
    rt = runtime
    (rt.kb / 'KB-901.md').write_text('legacytoken '*65+'tailtoken')
    first = rt.build()
    assert rt.build() == first
    assert all('source_start' in c and 'source_end' in c for c in first['chunks'])
    legacy = json.loads(Path(__file__).with_name('legacy-layout.json').read_text())
    # Rebase only input-directory identity so this is testing the layout version gate.
    old_key_code = "from kbqa import index; index.CHUNKER_VERSION='chunker-2'; print(index.content_key(__import__('pathlib').Path(__import__('os').environ['KB_DIR'])))"
    legacy['key'] = subprocess.check_output([sys.executable, '-c', old_key_code], cwd=rt.source, env=rt.env, text=True).strip()
    rt.cache.write_text(json.dumps(legacy))
    assert legacy['key'] != first['key']
    rt.http(['tailtoken'])  # automatic load, not forced rebuild
    assert json.loads(rt.cache.read_text()) == first


def assert_identity(rt, payload, query):
    from kbqa.retriever import Retriever
    index = load_index(Path(rt.env['KB_DIR']), rt.cache)
    result = Retriever(index, date(2026, 9, 1)).search(query, top_k=5)
    health, responses = rt.http([query])
    api = responses[query]['results']
    assert health['kb_chunks'] == len(payload['chunks'])
    assert len(api) == min(5, len(index.chunks))
    assert api == [h.as_result() for h in result.hits]
    by_id = {c.chunk_id: c for c in index.chunks}
    for hit, public in zip(result.hits, api):
        chunk = by_id[hit.chunk_id]
        assert hit.doc_id == chunk.doc_id == public['doc_id'], (query, hit.chunk_id, hit.doc_id, chunk.doc_id)
        assert hit.meta == index.docs_meta[chunk.doc_id] and hit.meta['doc_id'] == hit.doc_id
        assert hit.text == chunk.text and hit.source_text == chunk.source_text == public['text']
        assert hit.source_text == index.texts[hit.doc_id][hit.source_start:hit.source_end]
    assert [h.score for h in result.hits] == sorted((h.score for h in result.hits), reverse=True)
    return result


def test_duplicate_rerank_padding_identity_http(runtime):
    rt = runtime
    (rt.kb / 'KB-901.md').write_text(('dupetoken '*25 + '\n\n') * 5)
    (rt.kb / 'KB-902.md').write_text('dupetoken secondsource ' + 'filler '*20)
    (rt.kb / 'KB-903.md').write_text('unrelated thirdsource')
    payload = rt.build()
    # Multiple high-scoring candidates from 901 make deduplication observable.
    idx = load_index(rt.kb, rt.cache)
    scores = idx.score_terms({'dupetoken': 1})
    assert sum(idx.chunks[p].doc_id == 'KB-901' for p in scores) >= 3
    result = assert_identity(rt, payload, 'dupetoken')
    assert any(h.padded and h.score > 0 for h in result.hits)
    assert_identity(rt, payload, 'unmatchedzero')
    again = assert_identity(rt, rt.build(), 'dupetoken')
    assert [h.as_result() for h in result.hits] == [h.as_result() for h in again.hits]


def test_original_r08_r10_identity_http(runtime):
    rt = runtime
    rt.env['KB_DIR'] = str(ROOT / 'knowledge_base')
    payload = rt.build()
    questions = [json.loads(line) for line in (ROOT / 'eval/public_questions.jsonl').read_text().splitlines()]
    for q in questions:
        if q['id'] in ('R08', 'R10'):
            assert_identity(rt, payload, q['query'])
