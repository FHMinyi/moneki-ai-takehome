"""Version 1 lossless trace references; only known, exactly equal duplicates."""
from copy import deepcopy
import json

LIMIT = 2 * 1024 * 1024
MARKER = '_trace_references'

def compact_trace(payload: dict) -> dict:
    if MARKER in payload or len(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()) <= LIMIT:
        return payload
    result = deepcopy(payload)
    references = []
    def replace(path, target, encoding='identity'):
        source = _get(payload, target)
        if encoding == 'json-string':
            source = json.dumps(source, ensure_ascii=False)
        if json.dumps(_get(payload, path), ensure_ascii=False, sort_keys=True) != json.dumps(source, ensure_ascii=False, sort_keys=True):
            return
        _set(result, path, None)
        references.append({'path': path, 'target': target, 'encoding': encoding})
    for i, call in enumerate(payload.get('llm_calls', [])):
        if 'prompt' in call and 'messages' in call.get('request', {}):
            replace(['llm_calls', i, 'prompt'], ['llm_calls', i, 'request', 'messages'], 'json-string')
    steps = payload.get('steps', [])
    for i, step in enumerate(steps):
        detail = step.get('detail') or {}
        if (step.get('step') != 'tool' or detail.get('tool') != 'search_kb'
                or i < 2 or steps[i-2].get('step') != 'search'
                or steps[i-1].get('step') != 'document_evidence'):
            continue
        for key, target in [('diagnostics', ['steps', i-2, 'detail']),
                            ('evidence', ['steps', i-1, 'detail', 'evidence']),
                            ('rejected', ['steps', i-1, 'detail', 'rejected'])]:
            if key in detail.get('result', {}) and (key == 'diagnostics' or key in steps[i-1]['detail']):
                replace(['steps', i, 'detail', 'result', key], target)
    if references:
        result[MARKER] = {'version': 1, 'references': references}
    return result

def expand_trace(payload: dict) -> dict:
    """Reconstruct all original fields, including byte-identical prompt strings."""
    result = deepcopy(payload)
    metadata = result.pop(MARKER, None)
    if metadata is None:
        return result
    if metadata.get('version') != 1:
        raise ValueError('Unsupported trace reference version')
    for ref in metadata['references']:
        value = deepcopy(_get(result, ref['target']))
        if ref['encoding'] == 'json-string':
            value = json.dumps(value, ensure_ascii=False)
        elif ref['encoding'] != 'identity':
            raise ValueError('Unsupported trace reference encoding')
        _set(result, ref['path'], value)
    return result

def _get(value, path):
    for key in path:
        value = value[key]
    return value

def _set(value, path, replacement):
    _get(value, path[:-1])[path[-1]] = replacement
