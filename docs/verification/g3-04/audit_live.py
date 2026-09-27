"""Independently compare saved paid T01 evidence with SQLite and the ledger."""
from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "starter"))
from kbqa.config import load_settings
from kbqa.service import Service


def main():
    folder = Path(__file__).with_name("live")
    ledger = json.loads((folder / "ledger.json").read_text())
    assert ledger["chat_count"] == 3
    assert len(ledger["calls"]) == 6
    assert all(call["status"] == 200 and call["usage"] for call in ledger["calls"])
    assert abs(sum(call["accounted_cny"] for call in ledger["calls"]) - .050206) < 1e-9
    with tempfile.TemporaryDirectory(prefix="g304-audit-") as work:
        settings = replace(load_settings(), var_dir=Path(work), llm_base_url="",
                           llm_api_key="", llm_model="")
        service = Service(settings)
        questions = ["6 月的净营业额是多少？", "那 7 月呢？", "这两个月的客单价差了多少？"]
        expected = ["156757.00", "162414.00", "0.17"]
        for index, question in enumerate(questions, start=1):
            item = json.loads((folder / f"chat-{index}.json").read_text())
            assert item["request"] == {"session_id": "g304-paid-T01", "question": question}
            assert item["response"]["answer_type"] == "data"
            assert expected[index - 1] in item["response"]["answer"]
            trace = item["trace"]
            assert trace["errors"] == [] and len(trace["llm_calls"]) == 2
            context = next(s["detail"] for s in trace["steps"] if s["step"] == "session_context")
            assert context["history_size"] == index - 1
            tools = [s["detail"] for s in trace["steps"] if s["step"] == "tool"]
            assert len(tools) == 1
            actual = service.run_tool(tools[0]["tool"], tools[0]["params"])
            assert actual == tools[0]["result"]
            print(index, tools[0]["tool"], "SQLite matches", expected[index - 1])
    print("estimated_cny", ledger["conservative_committed_cny"], "billing_confirmed", ledger["billing_confirmed"])


if __name__ == "__main__":
    main()
