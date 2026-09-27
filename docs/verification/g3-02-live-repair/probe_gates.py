"""DIAGNOSTIC ONLY. In-memory ablation; never a product implementation."""
import sys,json
from pathlib import Path
HERE=Path(__file__).parent;ROOT=HERE.resolve().parents[2]
sys.path.insert(0,str(ROOT/'starter'))
import kbqa.document_binding as binding
import kbqa.document_evidence as evidence
from finalise_replay import run
source=Path(binding.__file__).read_text()
old='if not (same or same_entity or focus_match or translation):'
assert source.count(old)==1
namespace=dict(binding.__dict__)
exec(compile(source.replace(old,'if False: # DIAGNOSTIC: semantic equality gate disabled'),binding.__file__,'exec'),namespace)
evidence.check_binding=namespace['check_binding']
run(HERE/'probe-no-equality.json')
import pytest
sys.exit(pytest.main(['-q',str(ROOT/'docs/verification/g3-02/review-roles/test_roles.py'),str(ROOT/'docs/verification/g3-02/review-r1-r2/test_anchored_selection.py'), '--tb=short']))
