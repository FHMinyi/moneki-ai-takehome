"""Manually driven, at most two guarded real-browser chats on one fresh service.

Requires G305_FRESH, G305_OUT, G305_BASELINE and G305_PRIOR_CNY. Starts the
service and writes target-ready.json; sends no chat on its own. A separate
browser client must create target-done after the authorized two attempts.
"""

import json
import os
import subprocess
import time
from pathlib import Path

import httpx

if os.environ.get("G305_CHAT_LIMIT") != "2":
    raise RuntimeError("Target runner requires G305_CHAT_LIMIT=2")

import run_live_eval as guard


def main():
    if guard.BASELINE == guard.ORIGINAL_BASELINE:
        raise RuntimeError("Targeted real model checks need the new fixed point")
    if guard.state["chat_count"] or guard.state["attempts"]:
        raise RuntimeError("Prior target ledger exists; cannot restart")
    if not guard.output_limit_allowed(8192):
        raise RuntimeError("Fresh product output validator not available")
    guard.key = guard.load_key()
    guard.save()
    budget = guard.start_server("guard", 8134)
    relay = guard.start_server("relay", 8132)
    config = os.environ.copy()
    config.update(LLM_BASE_URL="http://127.0.0.1:8134/guard",
                  LLM_API_KEY="local-guard-dummy", LLM_MODEL="deepseek-flash")
    with (guard.OUT / "service.log").open("w") as log:
        service = subprocess.Popen(
            [str(guard.FRESH / "starter/.venv/bin/python"), "-m", "uvicorn",
             "kbqa.server:app", "--host", "127.0.0.1", "--port", "8133"],
            cwd=guard.FRESH / "starter", env=config, stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            with httpx.Client(trust_env=False, timeout=2) as client:
                for _ in range(100):
                    try:
                        health = client.get("http://127.0.0.1:8133/api/health").json()
                        break
                    except (httpx.HTTPError, ValueError):
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Target service did not start")
            assert health["llm_mode"] == "live"
            (guard.OUT / "health.json").write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n")
            ready = {"base_url": "http://127.0.0.1:8132", "max_chats": 2,
                     "baseline": guard.BASELINE,
                     "prior_conservative_cny": guard.PRIOR}
            (guard.OUT / "target-ready.json").write_text(json.dumps(ready, ensure_ascii=False, indent=2) + "\n")
            print("G305_TARGET_READY", json.dumps(ready), flush=True)
            deadline = time.monotonic() + 900
            while not (guard.OUT / "target-done").exists() and time.monotonic() < deadline:
                time.sleep(0.5)
            guard.save()
            print("G305_TARGET_FINISHED", json.dumps({
                "chat_count": guard.state["chat_count"],
                "attempts": len(guard.state["attempts"]),
                "conservative_committed_cny": guard.state["conservative_committed_cny"],
                "remaining_cny": guard.state["remaining_cny"]}), flush=True)
        finally:
            service.terminate()
            service.wait(timeout=10)
            relay.shutdown()
            budget.shutdown()
            guard.save()


if __name__ == "__main__":
    main()
