"""Real loader/index + subprocess rebuild/HTTP; no starter fixed-search fixture.
Run: starter/.venv/bin/python -m pytest docs/verification/g2-01/test_ingestion.py -q
G2_EVIDENCE optionally retains HTTP responses, commands, isolated paths and PIDs.
"""
import hashlib
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
from kbqa.loader import load_document, load_knowledge_base
from kbqa.index import load_index


def test_original_identity_and_formats(tmp_path):
    kb = ROOT / 'knowledge_base'
    expected = {p.name.split('_')[0] for p in kb.rglob('KB-*') if p.is_file()}
    index = load_index(kb, tmp_path / 'index.json')
    assert set(index.docs_meta) == expected


def test_filename_identity_not_frontmatter(tmp_path):
    p = tmp_path / 'KB-901.md'
    p.write_text('---\ndoc_id: KB-999\n---\nidentity')
    assert load_document(p).doc_id == 'KB-901'
    p = tmp_path / 'README.md'
    p.write_text('---\ndoc_id: KB-999\n---\nnot a document')
    assert load_document(p) is None


def test_actual_gbk_exact_text():
    p = next((ROOT / 'knowledge_base').rglob('KB-062*'))
    assert load_document(p).text == p.read_bytes().decode('gbk').strip('\n')


def test_invalid_encoding_never_silently_drops_bytes(tmp_path):
    p = tmp_path / 'KB-901.txt'
    p.write_bytes(b'bad\xff')
    with pytest.raises(UnicodeError):
        load_document(p)


def test_actual_html_visible_text():
    doc = load_document(next((ROOT / 'knowledge_base').rglob('KB-061*')))
    assert '发票在小程序“我的订单”里自助开具。' in doc.text
    assert 'window.dataLayer' not in doc.text
    assert '<style' not in doc.text and '<p' not in doc.text
    assert '© 2026' in doc.text and '&copy;' not in doc.text


def test_html_paragraphs_and_entities(tmp_path):
    p = tmp_path / 'KB-901.html'
    p.write_text('<head><title>FAQ</title><style>hiddenstyle</style></head>'
                 '<body><p>alpha &amp; beta</p><p>第二段<br>换行</p>'
                 '<script>hiddenjs</script></body>')
    doc = load_document(p)
    assert doc.title == 'FAQ'
    assert doc.text == 'alpha & beta\n第二段\n换行'


class Runtime:
    def __init__(self, root, name):
        self.root, self.name, self.records = root, name, []
        self.source = root / 'starter'
        shutil.copytree(ROOT / 'starter/kbqa', self.source / 'kbqa',
                        ignore=shutil.ignore_patterns('__pycache__'))
        self.kb = root / 'kb'
        self.kb.mkdir()
        self.env = os.environ.copy()
        for key in ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL', 'PYTHONPATH',
                    'DATA_DIR', 'KB_DIR', 'VAR_DIR', 'TODAY'):
            self.env.pop(key, None)
        self.env.update(PYTHONPATH=str(self.source), KB_DIR=str(self.kb),
                        DATA_DIR=str(ROOT / 'data'), VAR_DIR=str(root / 'var'))

    @property
    def cache(self):
        return self.source / '.cache/index.json'

    def build(self):
        cmd = [sys.executable, '-m', 'kbqa.rebuild']
        r = subprocess.run(cmd, cwd=self.source, env=self.env, capture_output=True, text=True)
        self.records.append(dict(command=cmd, cwd=str(self.source), exit_code=r.returncode,
                                 stdout=r.stdout, stderr=r.stderr))
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(self.cache.read_text())

    def http(self, queries=()):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cmd = [sys.executable, '-m', 'uvicorn', 'kbqa.server:app', '--host', '127.0.0.1', '--port', str(port)]
        with (self.root / 'server.log').open('a') as log:
            proc = subprocess.Popen(cmd, cwd=self.source, env=self.env, stdout=log, stderr=log)
            record = dict(command=cmd, pid=proc.pid, port=port, kb_dir=self.env['KB_DIR'])
            self.records.append(record)
            def request(path, body=None):
                req = urllib.request.Request(f'http://127.0.0.1:{port}' + path,
                    data=json.dumps(body).encode() if body is not None else None,
                    headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    return json.load(response)
            try:
                for _ in range(100):
                    try:
                        health = request('/api/health')
                        break
                    except OSError:
                        assert proc.poll() is None, (self.root / 'server.log').read_text()
                        time.sleep(.05)
                else:
                    raise AssertionError('startup timeout')
                results = {q: request('/api/retrieve', {'query': q, 'top_k': 5}) for q in queries}
                record.update(health=health, retrieval=results)
                return health, results
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                record['stopped'] = proc.poll() is not None


@pytest.fixture
def runtime(tmp_path, request):
    rt = Runtime(tmp_path, request.node.name)
    yield rt
    out = os.environ.get('G2_EVIDENCE')
    if out:
        path = Path(out)
        path.mkdir(parents=True, exist_ok=True)
        (path / (rt.name.replace('/', '_') + '.json')).write_text(json.dumps(
            dict(source=str(rt.source), records=rt.records), ensure_ascii=False, indent=2))


def assert_snapshot(rt, payload, expected, queries=()):
    health, responses = rt.http(queries)
    assert health['llm_mode'] == 'mock'
    assert health['kb_docs'] == len(payload['docs']) == len(expected)
    assert health['kb_chunks'] == len(payload['chunks'])
    assert payload['texts'] == expected
    for query, text in queries.items() if isinstance(queries, dict) else []:
        hits = responses[query]['results']
        assert any(text in h['text'] and h['score'] > 0 for h in hits), responses
    return responses


@pytest.mark.parametrize('suffix,body', [
    ('txt', 'mailtoken 邮件正文'),
    ('html', '<p>mailtoken 网页正文</p><script>hiddenjs</script>'),
])
def test_format_through_rebuild_http(runtime, suffix, body):
    rt = runtime
    (rt.kb / ('KB-901.' + suffix)).write_text(body)
    payload = rt.build()
    expected = 'mailtoken 邮件正文' if suffix == 'txt' else 'mailtoken 网页正文'
    assert_snapshot(rt, payload, {'KB-901': expected}, {'mailtoken': expected})


@pytest.mark.parametrize('change', ['add', 'modify', 'delete', 'switch'])
def test_lifecycle_rebuild_restart_http(runtime, change):
    rt = runtime
    p = rt.kb / 'KB-901.md'
    p.write_text('oldtoken oldfact')
    first = rt.build()
    assert_snapshot(rt, first, {'KB-901': 'oldtoken oldfact'}, {'oldtoken': 'oldfact'})
    if change == 'add':
        (rt.kb / 'KB-902.md').write_text('newtoken newfact')
        expected = {'KB-901': 'oldtoken oldfact', 'KB-902': 'newtoken newfact'}
    elif change == 'modify':
        p.write_text('newtoken newfact')
        expected = {'KB-901': 'newtoken newfact'}
    elif change == 'delete':
        p.unlink()
        expected = {}
    else:
        other = rt.root / 'other'
        other.mkdir()
        (other / 'KB-903.md').write_text('newtoken newfact')
        rt.env['KB_DIR'] = str(other)
        expected = {'KB-903': 'newtoken newfact'}
    second = rt.build()
    responses = assert_snapshot(rt, second, expected, {'newtoken': 'newfact'} if expected else {})
    if change != 'add':
        _, stale = rt.http(['oldtoken'])
        assert all('oldfact' not in h['text'] for h in stale['oldtoken']['results'])
    assert first['key'] != second['key']
    assert rt.build() == second


def test_metadata_alias_refresh_and_automatic_cache_invalidation(tmp_path):
    kb = tmp_path / 'kb'
    kb.mkdir()
    p = kb / 'KB-901.md'
    def document(title, alias):
        return f'---\ntitle: {title}\nstores: [S01]\n---\n|canonical|alias|\n|---|---|\n|product|{alias}|'
    p.write_text(document('oldtitle', 'oldalias'))
    cache = tmp_path / 'index.json'
    before = load_index(kb, cache)
    p.write_text(document('newtitle', 'newalias'))
    after = load_index(kb, cache)
    assert after.docs_meta['KB-901']['title'] == 'newtitle'
    assert after.aliases.resolve('newalias') == 'product'
    assert after.aliases.resolve('oldalias') == 'oldalias'
    assert before.key != after.key


def test_empty_and_non_document_health(runtime):
    rt = runtime
    (rt.kb / 'README.md').write_text('not a knowledge document')
    assert_snapshot(rt, rt.build(), {})
    health, results = rt.http(['anything'])
    assert health['kb_docs'] == health['kb_chunks'] == 0
    assert results['anything']['results'] == []


def test_first_start_and_legacy_cache_upgrade(runtime):
    rt = runtime
    (rt.kb / 'KB-901.md').write_text('newtoken newfact')
    assert not rt.cache.exists()
    health, responses = rt.http(['newtoken'])
    assert health['kb_docs'] == 1 and responses['newtoken']['results'][0]['score'] > 0
    # Real cache schema/key generated by the starting baseline, not a fake retriever.
    shutil.copyfile(Path(__file__).with_name('legacy-index.json'), rt.cache)
    payload = rt.build()
    assert_snapshot(rt, payload, {'KB-901': 'newtoken newfact'}, {'newtoken': 'newfact'})
    assert rt.build() == payload
