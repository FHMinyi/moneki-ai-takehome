"""Independent read-only SQLite audit of the two authorized live chats."""
import json
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = Path('/tmp/moneki-g306-paid-var/clean.db')
assert DB.exists(), 'The isolated rebuilt database must be retained for audit'
con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)


def one(sql, values):
    return con.execute(sql, values).fetchone()[0]


def expected(params):
    values = (params['start'], params['end'], params['store_id'])
    where = 'date >= ? AND date <= ? AND store_id = ?'
    net_cents = one(f'SELECT COALESCE(SUM(amount_cents),0) FROM sales_clean WHERE {where}', values)
    refund_cents = one(f'SELECT COALESCE(SUM(-amount_cents),0) FROM sales_clean WHERE {where} AND amount_cents < 0', values)
    orders = one(f'SELECT COUNT(DISTINCT order_id) FROM sales_clean WHERE {where} AND amount_cents > 0', values)
    sales_qty = one(f'SELECT COALESCE(SUM(qty),0) FROM sales_clean WHERE {where} AND amount_cents > 0', values)
    refund_qty = one(f'SELECT COALESCE(SUM(qty),0) FROM sales_clean WHERE {where} AND amount_cents < 0', values)
    net = Decimal(net_cents) / 100
    return {'start': params['start'], 'end': params['end'], 'store_id': params['store_id'],
            'product_id': None, 'net_revenue': float(net), 'refund_amount': float(Decimal(refund_cents)/100),
            'orders': orders, 'aov': float((net/Decimal(orders)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if orders else None,
            'qty': sales_qty - refund_qty}


ledger = json.loads((ROOT / 'live/ledger.json').read_text())
assert ledger['chat_count'] == 2 and len(ledger['calls']) == 4
assert all(call['status'] == 200 and isinstance(call.get('usage'), dict) for call in ledger['calls'])
assert ledger['conservative_committed_cny'] <= 6
audits = []
for number, scope in [(1, ('2026-06-01', '2026-06-30', 'S02')),
                      (2, ('2026-07-01', '2026-07-31', 'S01'))]:
    sample = json.loads((ROOT / f'live/chat-{number}.json').read_text())
    request, answer, trace = sample['request'], sample['response'], sample['trace']
    assert answer['answer_type'] == 'data' and len(answer['data_evidence']) == 1
    params = answer['data_evidence'][0]['params']
    assert (params['start'], params['end'], params['store_id']) == scope
    assert answer['data_evidence'][0]['tool'] == 'query_metrics'
    assert request['context'] == {'type': 'daily_trend', 'start': '2026-06-01', 'end': '2026-06-30',
                                  'store_id': 'S02', 'metric': 'net_revenue'}
    original = next(step['detail'] for step in trace['steps'] if step['step'] == 'request')
    resolution = next(step['detail'] for step in trace['steps'] if step['step'] == 'context_resolution')
    tool_step = next(step['detail'] for step in trace['steps'] if step['step'] == 'tool')
    assert original['question'] == request['question'] and original['context'] == request['context']
    assert (resolution['effective']['start'], resolution['effective']['end'], resolution['effective']['store_id']) == scope
    if number == 1:
        assert resolution['source']['window'] == 'reference' and resolution['source']['store_id'] == 'reference'
    else:
        assert resolution['source']['window'] == 'question' and resolution['source']['store_id'] == 'question'
    assert tool_step['params'] == params and tool_step['result'] == answer['data_evidence'][0]['result']
    want = expected(params)
    assert want == tool_step['result'], (want, tool_step['result'])
    assert f'{want["net_revenue"]:.2f}' in answer['answer']
    assert len(trace['llm_calls']) == 2 and not trace['errors']
    audits.append({'chat': number, 'commit': sample['commit'], 'question': request['question'],
                   'context': request['context'], 'resolution': resolution,
                   'tool_params': params, 'independent_sql_expected': want,
                   'actual_tool_result': tool_step['result'], 'answer': answer['answer'],
                   'trace_id': answer['trace_id'], 'model_attempts': len(trace['llm_calls'])})

(ROOT / 'live/independent-sql-audit.json').write_text(json.dumps({
    'database': str(DB), 'source': 'read-only SQLite aggregate queries in audit_live.py',
    'ledger_chats': ledger['chat_count'], 'ledger_outbound_attempts': len(ledger['calls']),
    'conservative_committed_cny': ledger['conservative_committed_cny'],
    'billing_confirmed': ledger['billing_confirmed'], 'audits': audits,
}, ensure_ascii=False, indent=2) + '\n')
print('independent SQLite audit: 2/2 complete; 4 model attempts; no trace errors')
