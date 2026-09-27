"""G3-06 only: at most two DeepSeek chats under a separate 6 CNY guard.

Every outbound attempt reserves 0.50 CNY before sending. Complete usage
releases the difference at peak cache-miss prices, conservatively converting
USD to CNY at 8.00. Missing usage or transport uncertainty retains reserve.
No balance or model-list probes. The ledger is reused, never reset here.
"""
import json
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent / 'live'
OUT.mkdir(exist_ok=True)
LEDGER_PATH = OUT / 'ledger.json'
ledger = json.loads(LEDGER_PATH.read_text()) if LEDGER_PATH.exists() else {
    'chat_count': 0, 'calls': [], 'limit_cny': 6, 'chat_limit': 2,
    'billing_confirmed': False, 'usd_cny_reserve_rate': 8.0,
    'official_peak_usd_per_m_input_cache_miss': 0.3,
    'official_peak_usd_per_m_output': 1.2,
}
lock = threading.Lock()


def save():
    ledger['conservative_committed_cny'] = sum(call['accounted_cny'] for call in ledger['calls'])
    ledger['remaining_cny'] = ledger['limit_cny'] - ledger['conservative_committed_cny']
    LEDGER_PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')


config = {}
# Credentials remain in the existing shared root; this worktree only reads them.
credential_file = Path(os.environ.get('G306_LIVE_ENV_PATH',
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
        if (self.path != '/guard/chat/completions' or len(raw) > 30000 or
                body.get('model') != 'deepseek-flash' or body.get('max_tokens') != 4096):
            self.respond(400, b'{"error":{"message":"guard configuration or size"}}')
            return
        with lock:
            if (ledger['chat_count'] > 2 or
                    sum(call['chat'] == ledger['chat_count'] for call in ledger['calls']) >= 6 or
                    sum(call['accounted_cny'] for call in ledger['calls']) + 0.50 > 6):
                self.respond(402, b'{"error":{"message":"G3-06 budget exhausted"}}')
                return
            entry = {'chat': ledger['chat_count'], 'attempt': len(ledger['calls']) + 1,
                     'request_bytes': len(raw), 'accounted_cny': 0.50,
                     'status': 'reserved', 'started_at': time.time()}
            ledger['calls'].append(entry)
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
                entry.update(status=response.status_code, elapsed_seconds=time.time()-entry['started_at'], usage=usage)
                if (isinstance(usage, dict) and type(usage.get('prompt_tokens')) is int and
                        type(usage.get('completion_tokens')) is int and usage['prompt_tokens'] >= 0 and
                        usage['completion_tokens'] >= 0):
                    cost = (usage['prompt_tokens'] * 2.4 + usage['completion_tokens'] * 9.6) / 1_000_000
                    entry.update(accounted_cny=cost, peak_cache_miss_estimate_cny=cost)
                else:
                    entry['note'] = 'Complete usage unavailable; 0.50 CNY reserve retained.'
                save()
            self.respond(response.status_code, response.text.replace(key, '[REDACTED]').encode())
        except Exception:
            with lock:
                entry.update(status='transport_error', note='Usage unknown; reserve retained.')
                save()
            self.respond(503, b'{"error":{"message":"guard transport failed"}}')


def main():
    if ledger['chat_count'] >= 2 or any(call['status'] == 'reserved' for call in ledger['calls']):
        raise RuntimeError('G3-06 chat limit reached or unresolved reservation')
    guard = ThreadingHTTPServer(('127.0.0.1', 0), Guard)
    threading.Thread(target=guard.serve_forever, daemon=True).start()
    with socket.socket() as port_probe:
        port_probe.bind(('127.0.0.1', 0))
        port = port_probe.getsockname()[1]
    environment = {**os.environ, 'LLM_BASE_URL': f'http://127.0.0.1:{guard.server_port}/guard',
                   'LLM_API_KEY': 'local-execution-dummy', 'LLM_MODEL': 'deepseek-flash',
                   'VAR_DIR': '/tmp/moneki-g306-paid-var', 'PYTHONPATH': str(ROOT / 'starter')}
    for name in ('DATA_DIR', 'KB_DIR'):
        environment.pop(name, None)
    reference = {'type': 'daily_trend', 'start': '2026-06-01', 'end': '2026-06-30',
                 'store_id': 'S02', 'metric': 'net_revenue'}
    questions = ['这段时间净营业额是多少？', '7月 S01 的净营业额是多少？']
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
                        if ledger['chat_count'] >= 2 or ledger['remaining_cny'] < 0.50:
                            break
                        ledger['chat_count'] += 1
                        number = ledger['chat_count']
                        save()
                    payload = {'session_id': f'g306-paid-{number}', 'question': question, 'context': reference}
                    answer = client.post(base + '/api/chat', json=payload).json()
                    trace = client.get(base + '/api/trace/' + answer['trace_id']).json()
                    (OUT / f'chat-{number}.json').write_text(json.dumps({
                        'request': payload, 'response': answer, 'trace': trace,
                        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    }, ensure_ascii=False, indent=2) + '\n')
                    print(f'chat {number}: {answer["answer_type"]}; {len(trace["llm_calls"])} model attempts', flush=True)
                    if answer['answer_type'] != 'data':
                        break
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
