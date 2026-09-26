"""Run diagnosis probes in an existing isolated baseline export; failing assertions are expected."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--baseline', type=Path, required=True)
args = parser.parse_args()
out = args.baseline.resolve()
meta = json.loads((out / 'environment.json').read_text())
source = Path(meta['source'])
if not source.is_dir():
    parser.error('Baseline export is missing; run baseline.py with a new --out first.')
env = os.environ.copy()
for key in ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL', 'DATA_DIR', 'KB_DIR', 'VAR_DIR', 'TODAY'):
    env.pop(key, None)
env.update(PYTHONPATH=str(source / 'starter'), G2_SOURCE=str(source), G2_OUT=str(out))
scripts = Path(__file__).resolve().parent
results = []
for repeat in (1, 2):
    command = [meta['python'], '-m', 'pytest', str(scripts / 'test_diagnostic_probes.py'), '-q', '--tb=short']
    result = subprocess.run(command, cwd=source, env=env, capture_output=True, text=True)
    (out / f'probes-{repeat}.txt').write_text(result.stdout + result.stderr)
    results.append({'command': command, 'exit_code': result.returncode})
    print(result.stdout.splitlines()[-1])
audit = subprocess.run([meta['python'], str(scripts / 'audit.py')], cwd=source, env=env, capture_output=True, text=True)
(out / 'audit.stdout.txt').write_text(audit.stdout + audit.stderr)
results.append({'audit_exit_code': audit.returncode})
(out / 'probe-commands.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
print(audit.stdout)
# Preserve a red exit status until the product defects are fixed.
raise SystemExit(max([r.get('exit_code', r.get('audit_exit_code', 0)) for r in results]))
