"""Credential removal at diagnostic/output boundaries; never shorten diagnostics."""
import json
from typing import Any


def redact(value: Any, secrets: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                # Raw text, JSON response bodies and exception reprs can encode a key.
                forms = {secret, json.dumps(secret, ensure_ascii=False)[1:-1],
                         json.dumps(secret, ensure_ascii=True)[1:-1], repr(secret)[1:-1]}
                for form in sorted(forms, key=len, reverse=True):
                    value = value.replace(form, '[REDACTED]')
        return value
    if isinstance(value, dict):
        return {redact(k, secrets): redact(v, secrets) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v, secrets) for v in value]
    return value
