"""Audit captured HTTP evidence, independent of the application selection code.
Usage: python audit.py HTTP_DIR OUT_JSON
Quote source checks are executed per build by test_doc_qa.quotes, including both
replacement snapshots; this audit checks admission and trace correspondence.
"""
import json
from pathlib import Path
import re
import sys
import unicodedata

root,out=map(Path,sys.argv[1:])
records=[]
for path in sorted(root.glob('*.json')):
    artifact=json.loads(path.read_text())
    for run in artifact['records']:
        requests=run.get('requests',[])
        traces={r['response']['trace_id']:r['response'] for r in requests if r['path'].startswith('/api/trace/')}
        for req in requests:
            if req['path']!='/api/chat':continue
            a=req['response'];t=traces[a['trace_id']]
            steps={s['step']:s['detail'] for s in t['steps']}
            norm=lambda s:re.sub(r'[\s*`|#>]','',unicodedata.normalize('NFKC',s))
            assert len(a['answer'])<=1200
            assert len({c['doc_id'] for c in a['citations']})<=4
            assert all(0<len(norm(c['quote']))<=400 for c in a['citations'])
            if a['answer_type']=='doc':
                assert steps['plan']['intent']=='doc' and not a['data_evidence']
                selected=steps['evidence']['selected'];hits=steps['search']['hits']
                assert selected
                for s in selected:
                    h=next(h for h in hits if h['chunk_id']==s['chunk_id'])
                    assert h['doc_id']==s['doc_id'] and h['score']>0 and not h['padded'] and not h['exclusion_reason']
                    assert dict(doc_id=s['doc_id'],quote=s['quote']) in a['citations']
                assert not any('9999999' in c['quote'] for c in a['citations'])
            records.append(dict(test=path.name,question=req['body']['question'],type=a['answer_type'],
                                trace_id=a['trace_id'],citations=a['citations'],
                                selected=steps.get('evidence',{}).get('selected',[]),errors=t['errors']))
result=dict(requests=len(records),document_answers=sum(r['type']=='doc' for r in records),
            trace_available=len(records),positive_nonpadding_source_mismatches=0,records=records)
out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='records'}))
