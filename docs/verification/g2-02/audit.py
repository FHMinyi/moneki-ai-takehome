"""Audit saved real HTTP responses against the exact isolated rebuilt index.
Usage: python audit.py /tmp/moneki-g2-02-final /tmp/g2-02-audit.json
"""
import hashlib
import json
from pathlib import Path
import sys

run = Path(sys.argv[1])
env = json.loads((run / 'environment.json').read_text())
payload = json.loads((Path(env['source']) / 'starter/.cache/index.json').read_text())
chunks = {c['chunk_id']: c for c in payload['chunks']}
assert len(chunks) == len(payload['chunks'])
docs = {}
for doc_id, text in payload['texts'].items():
    covered = set()
    local = [c for c in chunks.values() if c['doc_id'] == doc_id]
    for c in local:
        a, b = c['source_start'], c['source_end']
        assert 0 <= a < b <= len(text)
        assert c['source_text'] == text[a:b]
        assert c['source_text'].strip(), c['chunk_id']
        assert payload['docs'][doc_id]['doc_id'] == doc_id
        covered.update(range(a, b))
        for s in c['context_spans']:
            assert text[s['start']:s['end']] == s['text']
    docs[doc_id] = dict(characters=len(text), covered=len(covered), missing=len(text)-len(covered),
                       source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                       chunks=[dict(chunk_id=c['chunk_id'], start=c['source_start'], end=c['source_end'],
                                    kind=c['kind']) for c in local])
    assert docs[doc_id]['missing'] == 0
responses = json.loads((run / 'retrieval-responses.json').read_text())
checked = 0
for response in responses:
    for h in response['response']['results']:
        c = chunks[h['chunk_id']]
        assert h['doc_id'] == c['doc_id']
        assert h['text'] == c['source_text']
        assert h['retrieval_text'] == c['text']
        assert h['context_spans'] == c['context_spans']
        assert h['source_start'] == c['source_start'] and h['source_end'] == c['source_end']
        checked += 1
health = json.loads((run / 'health.json').read_text())
assert health['kb_chunks'] == len(chunks) and health['kb_docs'] == len(docs)
result = dict(commit=env['commit'], documents=len(docs), chunks=len(chunks),
              missing_characters=sum(d['missing'] for d in docs.values()),
              http_queries=len(responses), http_hits_checked=checked, mismatched_sources=0, docs=docs)
Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps({k:v for k,v in result.items() if k != 'docs'}))
