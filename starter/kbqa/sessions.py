"""对话历史。"""

from __future__ import annotations

import threading
from collections import OrderedDict
from copy import deepcopy
from typing import Optional

MAX_TURNS = 6
MAX_SESSIONS = 500


class SessionStore:
    """最近几轮对话，够解追问就行。"""

    def __init__(self, max_sessions: int = MAX_SESSIONS, max_turns: int = MAX_TURNS) -> None:
        self._turns: OrderedDict[str, list[dict]] = OrderedDict()
        self._lock = threading.Lock()
        self.max_sessions = max_sessions
        self.max_turns = max_turns

    def history(self, session_id: Optional[str]) -> list[dict]:
        with self._lock:
            return deepcopy(self._turns.get(session_id, [])) if session_id else []

    def append(self, session_id: Optional[str], turn: dict) -> None:
        if not session_id:
            return
        with self._lock:
            turns = self._turns.setdefault(session_id, [])
            turns.append(deepcopy(turn))
            del turns[: max(0, len(turns) - self.max_turns)]
            self._turns.move_to_end(session_id)
            while len(self._turns) > self.max_sessions:
                self._turns.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._turns.clear()
