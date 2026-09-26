"""Save actual source/loaded-text comparisons without touching the shared cache."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'starter'))
from kbqa.index import load_index
from kbqa.loader import load_document

out = Path(sys.argv[1])
with tempfile.TemporaryDirectory() as temp:
    index = load_index(ROOT / 'knowledge_base', Path(temp) / 'index.json')
    expected = sorted(p.name.split('_')[0] for p in (ROOT / 'knowledge_base').rglob('KB-*') if p.is_file())
    comparisons = {}
    for doc_id, encoding in [('KB-062', 'gbk'), ('KB-061', 'utf-8')]:
        path = next((ROOT / 'knowledge_base').rglob(doc_id + '*'))
        original = path.read_bytes().decode(encoding)
        text = load_document(path).text
        comparisons[doc_id] = dict(path=str(path.relative_to(ROOT)), encoding=encoding,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(), original=original, loaded_text=text)
        if encoding == 'gbk':
            assert original.strip('\n') == text
        else:
            quote = '发票在小程序“我的订单”里自助开具。'
            assert quote in original and quote in text
            assert 'window.dataLayer' not in text and '<style' not in text
            comparisons[doc_id]['continuous_quote'] = quote
    assert sorted(index.docs_meta) == expected
    out.write_text(json.dumps(dict(expected_ids=expected, indexed_ids=sorted(index.docs_meta),
        kb_docs=len(index.docs_meta), kb_chunks=len(index.chunks), comparisons=comparisons),
        ensure_ascii=False, indent=2))
print('Source comparisons verified; dynamic identity set matches complete index.')
