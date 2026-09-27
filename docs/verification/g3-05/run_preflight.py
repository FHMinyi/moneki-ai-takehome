"""Run the unchanged official preflight against a fresh G3-05 source export."""

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRESH = Path("/tmp/moneki-g305-fresh-4591fab")
sys.path.insert(0, str(ROOT / "eval"))
from llm_gateway import run_preflight  # noqa: E402

process = None


def ready(env):
    global process
    config = os.environ.copy()
    config.update(env)
    process = subprocess.Popen(
        [str(FRESH / "starter/.venv/bin/python"), "-m", "uvicorn", "kbqa.server:app",
         "--host", "127.0.0.1", "--port", "8130"],
        cwd=FRESH / "starter", env=config,
        stdout=(ROOT / "docs/verification/g3-05/preflight/service.log").open("w"),
        stderr=subprocess.STDOUT,
    )
    for _ in range(100):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8130/api/health", timeout=1) as r:
                assert b'"llm_mode":"live"' in r.read()
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("preflight service did not start")


try:
    result = run_preflight(
        "http://127.0.0.1:8130", no_wait=True,
        out_dir=str(ROOT / "docs/verification/g3-05/preflight"), ready_hook=ready,
    )
    print("PREFLIGHT_EXIT", 0 if result.passed else 1)
finally:
    if process is not None:
        process.terminate()
        process.wait(timeout=10)
