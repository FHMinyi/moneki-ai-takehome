"""Pure accounting rules for G3-04's three authorized live chats."""

RESERVE_CNY = 2.20
LIMIT_CNY = 10.0
MAX_CHATS = 3
MAX_ATTEMPTS_PER_CHAT = 14
PREVIOUS_STAGE_ESTIMATE_CNY = 1.167168
STAGE_LIMIT_CNY = 50.0
PREVIOUS_STAGE_CHATS = 9
STAGE_MAX_CHATS = 18
PEAK_INPUT_CACHE_MISS_CNY_PER_M = 2.0
PEAK_OUTPUT_CNY_PER_M = 8.0


def committed(ledger: dict) -> float:
    return sum(call['accounted_cny'] for call in ledger['calls'])


def can_reserve(ledger: dict) -> bool:
    chat = ledger['chat_count']
    return (1 <= chat <= MAX_CHATS and
            sum(call['chat'] == chat for call in ledger['calls']) < MAX_ATTEMPTS_PER_CHAT and
            committed(ledger) + RESERVE_CNY <= LIMIT_CNY and
            PREVIOUS_STAGE_ESTIMATE_CNY + committed(ledger) + RESERVE_CNY <= STAGE_LIMIT_CNY and
            PREVIOUS_STAGE_CHATS + chat <= STAGE_MAX_CHATS)


def reserve(ledger: dict, request_bytes: int, now: float) -> dict:
    if not can_reserve(ledger):
        raise ValueError('G3-04 budget exhausted; outbound request forbidden')
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
