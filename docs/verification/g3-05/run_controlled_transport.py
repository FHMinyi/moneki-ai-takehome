"""Free HTTP evidence for current typed answers with delayed response bodies."""

import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
FRESH = Path("/tmp/moneki-g305-fresh-4591fab")
OUT = ROOT / "docs/verification/g3-05/controlled-transport"
OUT.mkdir(exist_ok=True)
state = {"mode": "normal", "requests": []}


class Model(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        body = json.loads(raw)
        tools = [m for m in body["messages"] if m["role"] == "tool"]
        state["requests"].append({"mode": state["mode"], "path": self.path,
                                  "request": body})
        if state["mode"] == "timeout":
            time.sleep(4)
            return
        if not tools:
            response = {"choices": [{"finish_reason": "tool_calls", "message": {
                "role": "assistant", "content": "", "reasoning_content": "CONTROLLED_PRIVATE_REASONING",
                "tool_calls": [{"id": "controlled-query-1", "type": "function", "function": {
                    "name": "query_metrics", "arguments": json.dumps({
                        "start": "2026-06-01", "end": "2026-06-30", "store_id": "S02"
                    })}}],
            }}]}
        else:
            call = json.loads(tools[-1]["content"])["call_id"]
            response = {"choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": json.dumps({"answer_type": "data", "results": [
                    {"call_id": call, "metric": "net_revenue"}
                ]}), "reasoning_content": "CONTROLLED_PRIVATE_REASONING",
            }}]}
        response["usage"] = {"prompt_tokens": 1, "completion_tokens": 1}
        content = json.dumps(response).encode()
        # JSON whitespace before the body is legal and tests actual blocking
        # HTTP parsing. This is not an SSE stream; the product requests nonstream.
        prefix = b" \r\n" * 4 if state["mode"] == "delayed" else b""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(prefix) + len(content)))
        self.end_headers()
        try:
            if prefix:
                for _ in range(4):
                    self.wfile.write(b" \r\n")
                    self.wfile.flush()
                    time.sleep(0.4)
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    if (OUT / "results.json").exists():
        raise RuntimeError("Prior evidence exists; do not overwrite")
    model = ThreadingHTTPServer(("127.0.0.1", 0), Model)
    threading.Thread(target=model.serve_forever, daemon=True).start()
    config = os.environ.copy()
    config.update(LLM_BASE_URL=f"http://127.0.0.1:{model.server_port}/controlled",
                  LLM_API_KEY="controlled-only", LLM_MODEL="controlled-model")
    service_log = (OUT / "service.log").open("w")
    service = None
    records = []
    try:
        for mode, port, timeout in [("normal", 8135, 120), ("delayed", 8136, 120),
                                    ("timeout", 8137, 2)]:
            state["mode"] = mode
            env = dict(config, LLM_TIMEOUT=str(timeout))
            service = subprocess.Popen(
                [str(FRESH / "starter/.venv/bin/python"), "-m", "uvicorn",
                 "kbqa.server:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=FRESH / "starter", env=env, stdout=service_log,
                stderr=subprocess.STDOUT,
            )
            with httpx.Client(trust_env=False, timeout=30) as client:
                base = f"http://127.0.0.1:{port}"
                for _ in range(100):
                    try:
                        health = client.get(base + "/api/health").json()
                        break
                    except (httpx.HTTPError, ValueError):
                        time.sleep(0.1)
                assert health["llm_mode"] == "live"
                request = {"session_id": "g305-controlled-" + mode,
                           "question": "S02 6月净营业额是多少？"}
                started = time.monotonic()
                response = client.post(base + "/api/chat", json=request, timeout=30)
                elapsed = round(time.monotonic() - started, 3)
                answer = response.json()
                trace = client.get(base + "/api/trace/" + answer["trace_id"]).json()
                records.append({"mode": mode, "health": health, "request": request,
                                "http_status": response.status_code,
                                "elapsed_seconds": elapsed, "answer": answer,
                                "trace": trace})
            service.terminate()
            service.wait(timeout=10)
            service = None
        (OUT / "results.json").write_text(json.dumps({"records": records,
            "model_requests": state["requests"]}, ensure_ascii=False, indent=2) + "\n")
        print([(r["mode"], r["http_status"], r["answer"]["answer_type"],
                r["elapsed_seconds"]) for r in records])
    finally:
        if service is not None:
            service.terminate()
            service.wait(timeout=10)
        model.shutdown()
        model.server_close()
        service_log.close()


if __name__ == "__main__":
    main()
