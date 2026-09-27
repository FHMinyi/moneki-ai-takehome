"""Pure accounting rules for G3-06's two authorized live samples."""

RESERVE_CNY = 2.20
LIMIT_CNY = 6.0
MAX_CHATS = 2
MAX_ATTEMPTS_PER_CHAT = 6
PEAK_INPUT_CACHE_MISS_CNY_PER_M = 2.0
PEAK_OUTPUT_CNY_PER_M = 8.0


def committed(ledger: dict) -> float:
    return sum(call['accounted_cny'] for call in ledger['calls'])


def can_reserve(ledger: dict) -> bool:
    chat = ledger['chat_count']
    return (1 <= chat <= MAX_CHATS and
            sum(call['chat'] == chat for call in ledger['calls']) < MAX_ATTEMPTS_PER_CHAT and
            committed(ledger) + RESERVE_CNY <= LIMIT_CNY)


def reserve(ledger: dict, request_bytes: int, now: float) -> dict:
    if not can_reserve(ledger):
        raise ValueError('G3-06 budget exhausted; outbound request forbidden')
    entry = {'chat': ledger['chat_count'], 'attempt': len(ledger['calls']) + 1,
             'request_bytes': request_bytes, 'accounted_cny': RESERVE_CNY,
             'status': 'reserved', 'started_at': now}
    ledger['calls'].append(entry)
    return entry


def settle(entry: dict, status, usage, elapsed: float) -> None:
    entry.update(status=status, elapsed_seconds=elapsed, usage=usage)
    if (isinstance(usage, dict) and type(usage.get('prompt_tokens')) is int and
            type(usage.get('completion_tokens')) is int and
            usage['prompt_tokens'] >= 0 and usage['completion_tokens'] >= 0):
        cost = (usage['prompt_tokens'] * PEAK_INPUT_CACHE_MISS_CNY_PER_M +
                usage['completion_tokens'] * PEAK_OUTPUT_CNY_PER_M) / 1_000_000
        entry.update(accounted_cny=cost, peak_cache_miss_estimate_cny=cost)
    else:
        entry['note'] = 'Complete usage unavailable; 2.20 CNY reserve retained.'
