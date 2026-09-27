"""Independent disposable DB/KB replacement, rebuild, restart and HTTP checks."""

import json
import os
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
FRESH = Path("/tmp/moneki-g305-fresh-4591fab")
TEMP = Path("/tmp/moneki-g305-replaced-4591fab")
OUT = ROOT / "docs/verification/g3-05/replacement"
OUT.mkdir(exist_ok=True)
if TEMP.exists() or (OUT / "results.json").exists():
    raise RuntimeError("Existing replacement inputs/results; do not overwrite")
TEMP.mkdir()
shutil.copytree(FRESH / "data", TEMP / "data")
shutil.copytree(FRESH / "knowledge_base", TEMP / "knowledge_base")
db = TEMP / "data/pos.db"
con = sqlite3.connect(db)
con.execute("DELETE FROM sales")
con.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?)", [
    ("G305-SALE", "2026-06-18", "S02", "P06", "9", "210.00", "现金"),
    ("G305-REFUND", "2026-06-18", "S02", "P06", "2", "-60.00", "现金"),
    ("G305-OTHER", "2026-07-01", "S01", "P01", "1", "32.00", "现金"),
])
con.commit()
independent_rows = con.execute("SELECT order_id,qty,amount FROM sales WHERE date='2026-06-18' AND store_id='S02' AND product_id='P06' ORDER BY order_id").fetchall()
con.close()
assert independent_rows == [("G305-REFUND", "2", "-60.00"), ("G305-SALE", "9", "210.00")]
# Independent hand oracle: zero-dirty data, one sale 9 and one refund 2.
oracle = {"qty": 7, "net_revenue": 150.0, "target_initial": 10,
          "target_revised": 6, "first_met": False, "second_met": True}
kb = TEMP / "knowledge_base"
target_file = kb / "notices/KB-023_2026年618活动方案.md"
target = target_file.read_text()
assert target.count("120 份") == 2
target_file.write_text(target.replace("120 份", "10 份"))
policy_file = kb / "policies/KB-013_退款政策_v2.md"
policy = policy_file.read_text()
assert "24 小时" in policy
policy_file.write_text(policy.replace("24 小时", "30 小时"))
alias_file = kb / "handbook/KB-003_商品与门店别名词典.md"
alias = alias_file.read_text()
assert "牛肉波奇饭、Beef Poke" in alias
alias_file.write_text(alias.replace("牛肉波奇饭、Beef Poke", "牛肉波奇饭、Beef Poke、红岩饭"))
event_file = kb / "notices/KB-990_临时经营事件.md"
event_file.write_text("---\ndoc_id: KB-990\ntitle: S02 临时经营事件\ntype: 通知\nstatus: 现行\neffective_from: 2026-06-18\nstores: [S02]\n---\n\nS02 在 2026-06-18 因冷库检修暂停晚市营业。\n")

environment = os.environ.copy()
environment.update(DATA_DIR=str(TEMP / "data"), KB_DIR=str(kb),
                   VAR_DIR=str(TEMP / "var"))
for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
    environment.pop(name, None)


def rebuild(phase):
    with (OUT / f"rebuild-{phase}.txt").open("w") as f:
        subprocess.run([str(FRESH / "starter/.venv/bin/python"), "-m", "kbqa.rebuild"],
                       cwd=FRESH / "starter", env=environment, stdout=f,
                       stderr=subprocess.STDOUT, check=True)


def run(phase, port):
    with (OUT / f"server-{phase}.txt").open("w") as log:
        proc = subprocess.Popen([str(FRESH / "starter/.venv/bin/python"), "-m", "uvicorn",
            "kbqa.server:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=FRESH / "starter", env=environment, stdout=log,
            stderr=subprocess.STDOUT)
        try:
            base = f"http://127.0.0.1:{port}"
            with httpx.Client(trust_env=False, timeout=180) as client:
                for _ in range(100):
                    try:
                        health = client.get(base + "/api/health").json()
                        break
                    except (httpx.HTTPError, ValueError):
                        time.sleep(0.1)
                else:
                    raise RuntimeError("replacement service did not start")
                result = {"phase": phase, "health": health}
                params = "start=2026-06-18&end=2026-06-18&store_id=S02&product_id=P06"
                result["metrics"] = client.get(base + "/api/metrics/summary?" + params).json()
                result["retrieve_event"] = client.post(base + "/api/retrieve", json={
                    "query": "S02 6月18日冷库检修暂停晚市营业", "top_k": 5}).json()
                questions = [
                    "618 当天 S02 的牛肉poke 卖了多少份？达到目标了吗？",
                    "S02 6月18日红岩饭销量是多少？",
                    "外卖订单多久内可以申请退款？",
                    "2026年6月1日外卖订单多久内可以申请退款？",
                    "S02 6月18日为什么营业额偏低？",
                ]
                result["chats"] = []
                for n, question in enumerate(questions):
                    payload = {"session_id": f"g305-replacement-{phase}-{n}",
                               "question": question}
                    response = client.post(base + "/api/chat", json=payload).json()
                    trace = client.get(base + "/api/trace/" + response["trace_id"]).json()
                    result["chats"].append({"request": payload, "response": response,
                                            "trace": trace})
                return result
        finally:
            proc.terminate()
            proc.wait(timeout=10)


rebuild("initial")
first = run("initial", 8138)
target_file.write_text(target_file.read_text().replace("10 份", "6 份"))
event_file.unlink()  # Verify deleted KB-990 cannot remain in the rebuilt index.
rebuild("revised")
second = run("revised", 8139)
assert first["metrics"]["qty"] == second["metrics"]["qty"] == oracle["qty"]
assert first["metrics"]["net_revenue"] == second["metrics"]["net_revenue"] == oracle["net_revenue"]
assert any(x["doc_id"] == "KB-990" for x in first["retrieve_event"]["results"])
assert not any(x["doc_id"] == "KB-990" for x in second["retrieve_event"]["results"])
(OUT / "results.json").write_text(json.dumps({"oracle": oracle,
    "independent_sql_rows": independent_rows, "initial": first, "revised": second},
    ensure_ascii=False, indent=2) + "\n")
print("replacement", first["health"]["kb_docs"], second["health"]["kb_docs"],
      first["metrics"]["qty"], second["metrics"]["qty"],
      [(x["response"]["answer_type"]) for x in first["chats"]],
      [(x["response"]["answer_type"]) for x in second["chats"]])
