"""Free final-source HTTP proof for the preapproved trend question's comparison path."""

import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
FRESH = Path("/tmp/moneki-g305-final-c7084d6")
OUT = ROOT / "docs/verification/g3-05/final-c7084d6/fresh/controlled-prevweek.json"
requests = []


class Model(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        requests.append(body)
        prior = {"start_a": "2026-06-01", "end_a": "2026-06-07",
                 "start_b": "2026-06-08", "end_b": "2026-06-14", "store_id": "S03"}
        if not any(m["role"] == "tool" for m in body["messages"]):
            message = {"role": "assistant", "content": "", "reasoning_content": "controlled",
                       "tool_calls": [{"id": "controlled-prevweek", "type": "function",
                                       "function": {"name": "compare_periods",
                                                    "arguments": json.dumps(prior)}}]}
            finish = "tool_calls"
        else:
            message = {"role": "assistant", "content": '{"answer_type":"refusal","reason":"insufficient_evidence"}',
                       "reasoning_content": "controlled"}
            finish = "stop"
        response = json.dumps({"choices": [{"finish_reason": finish, "message": message}],
                               "usage": {"prompt_tokens": 1, "completion_tokens": 1}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


if OUT.exists():
    raise RuntimeError("Prior controlled proof exists")
server = ThreadingHTTPServer(("127.0.0.1", 0), Model)
threading.Thread(target=server.serve_forever, daemon=True).start()
env = os.environ.copy()
env.update(LLM_BASE_URL=f"http://127.0.0.1:{server.server_port}/controlled",
           LLM_API_KEY="controlled-only", LLM_MODEL="controlled-model")
with (ROOT / "docs/verification/g3-05/final-c7084d6/fresh/controlled-prevweek-service.txt").open("w") as log:
    proc = subprocess.Popen(["/tmp/moneki-g305-fresh-4591fab/starter/.venv/bin/python", "-m",
        "uvicorn", "kbqa.server:app", "--host", "127.0.0.1", "--port", "8142"],
        cwd=FRESH / "starter", env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        with httpx.Client(trust_env=False, timeout=180) as client:
            for _ in range(100):
                try:
                    client.get("http://127.0.0.1:8142/api/health").raise_for_status()
                    break
                except httpx.HTTPError:
                    time.sleep(0.1)
            payload = {"session_id": "g305-controlled-prevweek",
                       "question": "这段时间的净营业额为什么比前一周低？",
                       "context": {"type": "daily_trend", "start": "2026-06-08",
                                   "end": "2026-06-14", "store_id": "S03",
                                   "metric": "net_revenue"}}
            raw = client.post("http://127.0.0.1:8142/api/chat", json=payload)
            answer = raw.json()
            trace = client.get("http://127.0.0.1:8142/api/trace/" + answer["trace_id"]).json()
            OUT.write_text(json.dumps({"request": payload, "http_status": raw.status_code,
                "response": answer, "trace": trace, "model_requests": requests},
                ensure_ascii=False, indent=2) + "\n")
            print(raw.status_code, answer["answer_type"],
                  [(s["detail"].get("tool"), s["detail"].get("result"))
                   for s in trace["steps"] if s["step"] == "tool"])
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        server.shutdown()
        server.server_close()
