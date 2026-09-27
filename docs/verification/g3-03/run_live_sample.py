"""G3-03 only: at most four DeepSeek chats under a separate 12 CNY guard.

Every outbound attempt reserves 2.20 CNY before sending. Complete usage
releases the difference at official peak cache-miss RMB prices. Missing
usage or transport uncertainty retains the whole reserve.
No balance or model-list probes. The ledger is reused, never reset here.
"""
import json
import sys
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from live_budget import RESERVE_CNY, can_reserve, committed, reserve, settle

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent / 'live'
OUT.mkdir(exist_ok=True)
LEDGER_PATH = OUT / 'ledger.json'
ledger = json.loads(LEDGER_PATH.read_text()) if LEDGER_PATH.exists() else {
    'chat_count': 0, 'calls': [], 'limit_cny': 12, 'chat_limit': 4,
    'billing_confirmed': False,
    'prior_g3_estimate_cny': 1.167168, 'prior_directed_chats': 9,
    'g3_total_limit_cny': 50, 'directed_pool_limit': 18,
    'price_source': 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/',
    'price_checked_at_utc': '2026-09-27 06:42:23 UTC',
    'price_excerpt': 'deepseek-flash: 1M context; peak cache-miss input 2 CNY / 1M tokens; peak output 8 CNY / 1M tokens',
    'reserve_basis': '1,048,576 input tokens * 2/M + 4,096 output tokens * 8/M = 2.12992 CNY; reserve 2.20 CNY per outbound attempt',
}
lock = threading.Lock()


def save():
    ledger['conservative_committed_cny'] = committed(ledger)
    ledger['remaining_cny'] = ledger['limit_cny'] - ledger['conservative_committed_cny']
    LEDGER_PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')


config = {}
# Credentials remain in the existing shared root; this worktree only reads them.
credential_file = Path(os.environ.get('G303_LIVE_ENV_PATH',
    '/Volumes/MACPSSD/project/moneki-ai-takehome/.env.live'))
for line in credential_file.read_text().splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        name, value = line.split('=', 1)
        config[name.strip()] = value.strip().strip('"\'')
assert config['LLM_BASE_URL'].rstrip('/') == 'https://api.deepseek.com'
assert config['LLM_MODEL'] == 'deepseek-flash'
key = config['LLM_API_KEY']


class Guard(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, status, body):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        raw = self.rfile.read(int(self.headers['Content-Length']))
        try:
            body = json.loads(raw)
        except ValueError:
            self.respond(400, b'{"error":{"message":"invalid guarded request"}}')
            return
        if (self.path != '/guard/chat/completions' or len(raw) > 250000 or
                body.get('model') != 'deepseek-flash' or body.get('max_tokens') != 4096):
            self.respond(400, b'{"error":{"message":"guard configuration or size"}}')
            return
        with lock:
            if not can_reserve(ledger):
                self.respond(402, b'{"error":{"message":"G3-03 budget exhausted"}}')
                return
            entry = reserve(ledger, len(raw), time.time())
            save()
        try:
            with httpx.Client(trust_env=False, timeout=125) as client:
                response = client.post('https://api.deepseek.com/chat/completions', json=body,
                                       headers={'Authorization': 'Bearer ' + key})
            usage = None
            try:
                usage = response.json().get('usage')
            except (ValueError, AttributeError):
                pass
            with lock:
                settle(entry, response.status_code, usage, time.time()-entry['started_at'])
                save()
            (OUT / ('api-%s.json' % entry['attempt'])).write_text(json.dumps({'request': body, 'status': response.status_code, 'response': response.text.replace(key, '[REDACTED]')}, ensure_ascii=False, indent=2))
            self.respond(response.status_code, response.text.replace(key, '[REDACTED]').encode())
        except Exception:
            with lock:
                entry.update(status='transport_error', note='Usage unknown; 2.20 CNY reserve retained.')
                save()
            self.respond(503, b'{"error":{"message":"guard transport failed"}}')


def main():
    if ledger['chat_count'] >= 4 or any(call['status'] == 'reserved' for call in ledger['calls']):
        raise RuntimeError('G3-03 chat limit reached or unresolved reservation')
    with lock:
        save()
    guard = ThreadingHTTPServer(('127.0.0.1', 0), Guard)
    threading.Thread(target=guard.serve_forever, daemon=True).start()
    with socket.socket() as port_probe:
        port_probe.bind(('127.0.0.1', 0))
        port = port_probe.getsockname()[1]
    environment = {**os.environ, 'LLM_BASE_URL': f'http://127.0.0.1:{guard.server_port}/guard',
                   'LLM_API_KEY': 'local-execution-dummy', 'LLM_MODEL': 'deepseek-flash',
                   'VAR_DIR': '/tmp/moneki-g303-paid-var', 'PYTHONPATH': str(ROOT / 'starter')}
    for name in ('DATA_DIR', 'KB_DIR'):
        environment.pop(name, None)
    from test_mixed import QUESTIONS
    assert len(sys.argv) == 2 and sys.argv[1] in ('H01','H02','H03','H04','H05','H06')
    questions = [QUESTIONS[sys.argv[1]]]
    with (OUT / 'service.txt').open('a') as log:
        process = subprocess.Popen([str(ROOT / 'starter/.venv/bin/python'), '-m', 'uvicorn',
                                    'kbqa.server:app', '--host', '127.0.0.1', '--port', str(port)],
                                   cwd=ROOT, env=environment, stdout=log, stderr=log)
        try:
            base = f'http://127.0.0.1:{port}'
            with httpx.Client(trust_env=False, timeout=185) as client:
                for _ in range(100):
                    try:
                        health = client.get(base + '/api/health').json()
                        break
                    except (httpx.HTTPError, ValueError):
                        time.sleep(0.1)
                assert health['llm_mode'] == 'live'
                for question in questions:
                    with lock:
                        if ledger['chat_count'] >= 4 or ledger['remaining_cny'] < RESERVE_CNY:
                            break
                        ledger['chat_count'] += 1
                        number = ledger['chat_count']
                        save()
                    payload = {'session_id': f'g303-paid-{number}', 'question': question}
                    answer = client.post(base + '/api/chat', json=payload).json()
                    trace = client.get(base + '/api/trace/' + answer['trace_id']).json()
                    (OUT / f'chat-{number}.json').write_text(json.dumps({
                        'request': payload, 'response': answer, 'trace': trace,
                        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    }, ensure_ascii=False, indent=2) + '\n')
                    print(f'chat {number}: {answer["answer_type"]}; {len(trace["llm_calls"])} model attempts', flush=True)
                    print(answer['answer'], flush=True)
        finally:
            process.terminate()
            process.wait(timeout=10)
            guard.shutdown()
            guard.server_close()
            with lock:
                save()
    print(json.dumps({k: ledger[k] for k in ('chat_count', 'conservative_committed_cny',
                                            'remaining_cny', 'billing_confirmed')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
