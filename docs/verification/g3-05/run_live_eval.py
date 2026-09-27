"""One unchanged public evaluation through a per-attempt CNY guard.

The key is read only from the existing shared .env.live. Every actual upstream
attempt, including retries, is reserved before transmission and journaled.
The evaluator-facing relay retains each chat and trace without editing eval.
"""

import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
FRESH = Path(os.environ.get("G305_FRESH", "/tmp/moneki-g305-fresh-4591fab"))
PYTHON = Path(os.environ.get("G305_PYTHON", str(FRESH / "starter/.venv/bin/python")))
OUT = Path(os.environ.get("G305_OUT", str(ROOT / "docs/verification/g3-05/eval-live")))
BASELINE = os.environ.get("G305_BASELINE", "4591fab9a80ef63c440b9a117dbbc4fcbf03c430")
ORIGINAL_BASELINE = "4591fab9a80ef63c440b9a117dbbc4fcbf03c430"
if BASELINE != ORIGINAL_BASELINE and "G305_PRIOR_CNY" not in os.environ:
    raise RuntimeError("Integrated recheck requires the latest prior CNY ledger amount")
OUT.mkdir(exist_ok=True)
LEDGER = OUT / "ledger.json"
TRAFFIC = OUT / "model-traffic.jsonl"
CHATS = OUT / "chat-trace.jsonl"
PRIOR = float(os.environ.get("G305_PRIOR_CNY", "1.440556"))
LIMIT = 50.0
RESERVE = 2.20
CHAT_LIMIT = int(os.environ.get("G305_CHAT_LIMIT", "0"))
if CHAT_LIMIT < 0:
    raise RuntimeError("Invalid targeted chat limit")
if not 0 <= PRIOR < LIMIT:
    raise RuntimeError("Invalid prior conservative CNY amount")
lock = threading.RLock()
state = json.loads(LEDGER.read_text()) if LEDGER.exists() else {
    "baseline_commit": BASELINE,
    "prior_conservative_cny": PRIOR,
    "total_authorized_cny": LIMIT,
    "reserve_per_attempt_cny": RESERVE,
    "price_peak_cache_miss_input_cny_per_m": 2.0,
    "price_peak_output_cny_per_m": 8.0,
    "billing_confirmed": False,
    "attempts": [],
    "chat_count": 0,
    "active_chat": None,
}
key = None


def save():
    state["conservative_committed_cny"] = round(
        PRIOR + sum(a["accounted_cny"] for a in state["attempts"]), 6)
    state["remaining_cny"] = round(LIMIT - state["conservative_committed_cny"], 6)
    temp = LEDGER.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    temp.replace(LEDGER)


def append(path, value):
    with path.open("a") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")


def redact(value):
    return value.replace(key, "[REDACTED]") if key else value


def output_limit_allowed(value):
    """The 2.20 CNY reserve covers at most 8192 output tokens."""
    if not (type(value) is int and 1 <= value <= 8192):
        return False
    sys.path.insert(0, str(FRESH / "starter"))
    try:
        from kbqa.llm import valid_output_limit
    except ImportError:
        # Original 4591fab did not export this validator. Preserve its 4096
        # checkpoint; the integrated rerun must use the product validator.
        return BASELINE == ORIGINAL_BASELINE
    return valid_output_limit(value)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.server.kind != "relay":
            self.reply(404, b"{}")
            return
        self.forward(b"")

    def do_POST(self):
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        except (ValueError, OSError):
            self.reply(400, b"{}")
            return
        if self.server.kind == "guard":
            self.guard(raw)
        else:
            self.forward(raw)

    def guard(self, raw):
        try:
            body = json.loads(raw)
            assert self.path == "/guard/chat/completions"
            assert body.get("model") == "deepseek-flash"
            assert output_limit_allowed(body.get("max_tokens"))
            assert len(raw) <= 2_000_000
        except (ValueError, AssertionError):
            self.reply(400, b'{"error":{"message":"G305 guard rejected request"}}')
            return
        with lock:
            save()
            if state["remaining_cny"] < RESERVE or any(
                a["status"] == "reserved" for a in state["attempts"]
            ):
                self.reply(402, b'{"error":{"message":"G305 budget unavailable"}}')
                return
            attempt = {
                "attempt": len(state["attempts"]) + 1,
                "chat": state["active_chat"],
                "started_at_unix": time.time(),
                "request_bytes": len(raw),
                "status": "reserved",
                "accounted_cny": RESERVE,
            }
            state["attempts"].append(attempt)
            save()
        response_status = "transport_error"
        response_text = ""
        usage = None
        try:
            with httpx.Client(trust_env=False, timeout=125) as client:
                response = client.post(
                    "https://api.deepseek.com/chat/completions", content=raw,
                    headers={"Authorization": "Bearer " + key,
                             "Content-Type": "application/json"},
                )
            response_status = response.status_code
            response_text = redact(response.text)
            try:
                usage = response.json().get("usage")
            except (ValueError, AttributeError):
                pass
            self.reply(response.status_code, response_text.encode())
        except Exception as exc:
            response_text = type(exc).__name__
            self.reply(503, b'{"error":{"message":"G305 upstream transport failed"}}')
        finally:
            with lock:
                attempt["status"] = response_status
                attempt["elapsed_seconds"] = round(time.time() - attempt["started_at_unix"], 3)
                attempt["usage"] = usage
                if (isinstance(usage, dict)
                    and type(usage.get("prompt_tokens")) is int
                    and type(usage.get("completion_tokens")) is int
                    and usage["prompt_tokens"] >= 0
                    and usage["completion_tokens"] >= 0):
                    cost = (2 * usage["prompt_tokens"] + 8 * usage["completion_tokens"]) / 1_000_000
                    attempt["accounted_cny"] = round(cost, 6)
                else:
                    attempt["note"] = "Usage incomplete; full 2.20 CNY reservation retained"
                save()
                append(TRAFFIC, {
                    "attempt": attempt["attempt"], "chat": attempt["chat"],
                    "request": body, "status": response_status,
                    "response": response_text, "usage": usage,
                })

    def forward(self, raw):
        if self.path == "/api/chat" and self.command == "POST":
            with lock:
                if CHAT_LIMIT and state["chat_count"] >= CHAT_LIMIT:
                    self.reply(429, b'{"error":"G305 targeted chat limit reached"}')
                    return
                state["chat_count"] += 1
                state["active_chat"] = state["chat_count"]
                save()
                chat = state["chat_count"]
        else:
            chat = state["active_chat"]
        try:
            with httpx.Client(trust_env=False, timeout=185) as client:
                response = client.request(
                    self.command, "http://127.0.0.1:8133" + self.path,
                    content=raw if self.command == "POST" else None,
                    headers={"Content-Type": "application/json"},
                )
            text = redact(response.text)
            self.reply(response.status_code, text.encode(), response.headers.get("content-type", "application/json"))
            if self.path == "/api/chat" or self.path.startswith("/api/trace/"):
                with lock:
                    append(CHATS, {
                        "chat": chat, "path": self.path,
                        "request": json.loads(raw) if raw else None,
                        "status": response.status_code,
                        "response": json.loads(text) if text else None,
                    })
        except Exception as exc:
            self.reply(503, json.dumps({"error": type(exc).__name__}).encode())


def load_key():
    config = {}
    for line in Path("/Volumes/MACPSSD/project/moneki-ai-takehome/.env.live").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            name, value = line.split("=", 1)
            config[name.strip()] = value.strip().strip("\"'")
    assert config.get("LLM_BASE_URL", "").rstrip("/") == "https://api.deepseek.com"
    assert config.get("LLM_MODEL") == "deepseek-flash"
    assert config.get("LLM_API_KEY")
    return config["LLM_API_KEY"]


def start_server(kind, port):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.kind = kind
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    global key
    if state["baseline_commit"] != BASELINE:
        raise RuntimeError("Ledger fixed point differs from requested baseline")
    if state["prior_conservative_cny"] != PRIOR:
        raise RuntimeError("Ledger prior amount differs from requested amount")
    if BASELINE != ORIGINAL_BASELINE and not output_limit_allowed(8192):
        raise RuntimeError("Integrated product output limit validator unavailable")
    if state["chat_count"] or state["attempts"] or TRAFFIC.exists() or CHATS.exists():
        raise RuntimeError("Existing live evidence; never overwrite or rerun this runner")
    key = load_key()
    save()
    guard = start_server("guard", 8134)
    relay = start_server("relay", 8132)
    config = os.environ.copy()
    config.update(LLM_BASE_URL="http://127.0.0.1:8134/guard",
                  LLM_API_KEY="local-guard-dummy", LLM_MODEL="deepseek-flash")
    service_log = (OUT / "service.log").open("w")
    service = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "kbqa.server:app",
         "--host", "127.0.0.1", "--port", "8133"],
        cwd=FRESH / "starter", env=config, stdout=service_log,
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
                raise RuntimeError("Live service did not start")
        assert health["llm_mode"] == "live"
        (OUT / "health.json").write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n")
        command = [str(PYTHON),
                   str(FRESH / "eval/run_eval.py"),
                   "--base-url", "http://127.0.0.1:8132",
                   "--questions", str(FRESH / "eval/public_questions.jsonl"),
                   "--out", str(OUT)]
        with (OUT / "console.txt").open("w") as console:
            result = subprocess.run(command, cwd=FRESH, stdout=console,
                                    stderr=subprocess.STDOUT, timeout=7200)
        (OUT / "eval.exit").write_text(str(result.returncode) + "\n")
        print(json.dumps({"eval_exit": result.returncode,
                          "chats": state["chat_count"],
                          "attempts": len(state["attempts"]),
                          "committed_cny": state["conservative_committed_cny"],
                          "remaining_cny": state["remaining_cny"]}, ensure_ascii=False))
    finally:
        service.terminate()
        service.wait(timeout=10)
        service_log.close()
        relay.shutdown()
        guard.shutdown()
        save()


if __name__ == "__main__":
    main()
