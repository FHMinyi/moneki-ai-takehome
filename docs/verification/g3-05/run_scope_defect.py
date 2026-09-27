"""Add an adjacent-day row to expose a replacement-date parsing error."""

import json
import os
import sqlite3
import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
FRESH = Path("/tmp/moneki-g305-fresh-4591fab")
TEMP = Path("/tmp/moneki-g305-replaced-4591fab")
OUT = ROOT / "docs/verification/g3-05/replacement/scope-defect.json"
if OUT.exists():
    raise RuntimeError("Prior defect evidence exists")
db = TEMP / "data/pos.db"
con = sqlite3.connect(db)
con.execute("UPDATE sales SET store_id='S02',product_id='P06',qty='5',amount='100.00' WHERE order_id='G305-OTHER'")
con.commit()
rows = con.execute("SELECT order_id,date,qty,amount FROM sales WHERE store_id='S02' AND product_id='P06' ORDER BY date,order_id").fetchall()
con.close()
assert len(rows) == 3
env = os.environ.copy()
env.update(DATA_DIR=str(TEMP / "data"), KB_DIR=str(TEMP / "knowledge_base"),
           VAR_DIR=str(TEMP / "var"))
for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
    env.pop(name, None)
with (ROOT / "docs/verification/g3-05/replacement/rebuild-scope.txt").open("w") as f:
    subprocess.run([str(FRESH / "starter/.venv/bin/python"), "-m", "kbqa.rebuild"],
                   cwd=FRESH / "starter", env=env, stdout=f,
                   stderr=subprocess.STDOUT, check=True)
with (ROOT / "docs/verification/g3-05/replacement/server-scope.txt").open("w") as log:
    proc = subprocess.Popen([str(FRESH / "starter/.venv/bin/python"), "-m", "uvicorn",
        "kbqa.server:app", "--host", "127.0.0.1", "--port", "8140"],
        cwd=FRESH / "starter", env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        with httpx.Client(trust_env=False, timeout=180) as client:
            for _ in range(100):
                try:
                    client.get("http://127.0.0.1:8140/api/health").raise_for_status()
                    break
                except httpx.HTTPError:
                    time.sleep(0.1)
            base = "http://127.0.0.1:8140"
            metrics = client.get(base + "/api/metrics/summary?start=2026-06-18&end=2026-06-18&store_id=S02&product_id=P06").json()
            payload = {"session_id": "g305-alias-date-defect",
                       "question": "S02 6月18日红岩饭销量是多少？"}
            response = client.post(base + "/api/chat", json=payload).json()
            trace = client.get(base + "/api/trace/" + response["trace_id"]).json()
            OUT.write_text(json.dumps({"independent_sql_rows": rows,
                "hand_expected_june_18_qty": 9 - 2,
                "metrics_exact_day": metrics, "request": payload,
                "response": response, "trace": trace}, ensure_ascii=False, indent=2) + "\n")
            print("exact", metrics["qty"], "chat", response["answer_type"],
                  response["data_evidence"][0]["params"],
                  response["data_evidence"][0]["result"]["qty"])
    finally:
        proc.terminate()
        proc.wait(timeout=10)
