"""Reproduce the exact-day result over an actual local HTTP server."""
from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(os.environ.get("G304_DATE_HTTP_OUTPUT",
                          Path(__file__).with_name("actual-http.json")))


def prepare(work: Path):
    data = work / "data"
    data.mkdir()
    source = data / "pos.db"
    shutil.copy2(ROOT / "data/pos.db", source)
    with sqlite3.connect(source) as conn:
        conn.execute("DELETE FROM sales")
        conn.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?)", [
            ("SCOPE-SALE", "2026-06-18", "S02", "P06", "9", "210.00", "微信"),
            ("SCOPE-REFUND", "2026-06-18", "S02", "P06", "2", "-60.00", "微信"),
            ("SCOPE-ADJACENT", "2026-07-01", "S02", "P06", "5", "100.00", "微信"),
        ])
        rows = conn.execute("SELECT date,qty,amount FROM sales ORDER BY date,order_id").fetchall()
    kb = work / "knowledge_base"
    shutil.copytree(ROOT / "knowledge_base", kb)
    alias = kb / "handbook/KB-003_商品与门店别名词典.md"
    old = alias.read_text()
    anchor = "牛肉poke | 牛肉波奇饭、Beef Poke"
    assert anchor in old
    alias.write_text(old.replace(anchor, anchor + "、红岩饭"))
    return data, kb, rows


def main():
    if OUT.exists():
        raise RuntimeError("Existing HTTP evidence must not be overwritten")
    with tempfile.TemporaryDirectory(prefix="g304-date-http-") as temporary:
        work = Path(temporary)
        data, kb, rows = prepare(work)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        env = {**os.environ, "DATA_DIR": str(data), "KB_DIR": str(kb),
               "VAR_DIR": str(work / "var"), "PYTHONPATH": str(ROOT / "starter")}
        for key in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
            env.pop(key, None)
        with (work / "server.log").open("w") as log:
            process = subprocess.Popen([str(ROOT / ".venv/bin/python"), "-m", "uvicorn",
                                        "kbqa.server:app", "--host", "127.0.0.1",
                                        "--port", str(port)], cwd=ROOT, env=env,
                                       stdout=log, stderr=subprocess.STDOUT)
            try:
                base = f"http://127.0.0.1:{port}"
                with httpx.Client(trust_env=False, timeout=15) as client:
                    for _ in range(100):
                        try:
                            health = client.get(base + "/api/health").json()
                            break
                        except (httpx.HTTPError, ValueError):
                            time.sleep(.1)
                    else:
                        raise RuntimeError("HTTP service did not become ready")
                    assert health["llm_mode"] == "mock"
                    exact = client.get(base + "/api/metrics/summary", params={
                        "start": "2026-06-18", "end": "2026-06-18",
                        "store_id": "S02", "product_id": "P06"}).json()
                    assert exact["qty"] == 7
                    turns = []
                    cases = [
                        ("exact", "S02 6月18日红岩饭销量是多少？", None, 7, "2026-06-18"),
                        ("other-day", "S02 7月1日红岩饭销量是多少？", None, 5, "2026-07-01"),
                        ("no-day", "S02 红岩饭销量是多少？", None, 12, "2026-06-18"),
                        ("trend-override", "S02 6月18日红岩饭销量是多少？",
                         {"type": "daily_trend", "start": "2026-07-01", "end": "2026-07-01",
                          "store_id": "S02", "metric": "net_revenue"}, 7, "2026-06-18"),
                    ]
                    for sid, question, context, qty, start in cases:
                        payload = {"session_id": sid, "question": question}
                        if context:
                            payload["context"] = context
                        response = client.post(base + "/api/chat", json=payload)
                        assert response.status_code == 200
                        answer = response.json()
                        trace = client.get(base + "/api/trace/" + answer["trace_id"]).json()
                        evidence = answer["data_evidence"][0]
                        assert evidence["params"]["start"] == start
                        assert evidence["result"]["qty"] == qty
                        turns.append({"request": payload, "response": answer, "trace": trace})
                OUT.write_text(json.dumps({"source_rows": rows, "hand_expected_exact_qty": 9 - 2,
                                           "metrics_exact_day": exact, "turns": turns},
                                          ensure_ascii=False, indent=2) + "\n")
                print("HTTP 4/4; exact 7, adjacent 5, whole 12, trend override 7")
            finally:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
