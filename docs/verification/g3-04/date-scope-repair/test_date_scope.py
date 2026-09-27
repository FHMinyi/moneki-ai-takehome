"""Replacement-data date scope regression, independent of starter/tests' fake retriever."""
from __future__ import annotations

import shutil
import json
import os
import sqlite3
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "starter"))
from kbqa import server
from kbqa.config import load_settings
from kbqa.service import Service
from kbqa.timeparse import parse_time
from kbqa.llm import LLMClient, LLMReply


@pytest.fixture
def replacement(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    source = data_dir / "pos.db"
    shutil.copy2(ROOT / "data/pos.db", source)
    with sqlite3.connect(source) as conn:
        conn.execute("DELETE FROM sales")
        conn.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?)", [
            ("SCOPE-SALE", "2026-06-18", "S02", "P06", "9", "210.00", "微信"),
            ("SCOPE-REFUND", "2026-06-18", "S02", "P06", "2", "-60.00", "微信"),
            ("SCOPE-ADJACENT", "2026-07-01", "S02", "P06", "5", "100.00", "微信"),
        ])
    kb_dir = tmp_path / "knowledge_base"
    shutil.copytree(ROOT / "knowledge_base", kb_dir)
    alias_file = kb_dir / "handbook/KB-003_商品与门店别名词典.md"
    source_text = alias_file.read_text()
    anchor = "牛肉poke | 牛肉波奇饭、Beef Poke"
    assert anchor in source_text
    alias_file.write_text(source_text.replace(anchor, anchor + "、红岩饭"))
    service = Service(replace(load_settings(), data_dir=data_dir, kb_dir=kb_dir,
                              var_dir=tmp_path / "var", llm_base_url="",
                              llm_api_key="", llm_model=""))
    monkeypatch.setattr(server, "_service", service)
    return service, TestClient(server.app), source


def ask(client, service, session_id, question, context=None):
    request = {"session_id": session_id, "question": question}
    if context:
        request["context"] = context
    response = client.post("/api/chat", json=request)
    assert response.status_code == 200
    answer = response.json()
    trace = service.get_trace(answer["trace_id"])
    assert trace["errors"] == []
    return request, answer, trace


def assert_exact_day(answer, day, qty):
    assert answer["answer_type"] == "data"
    assert len(answer["data_evidence"]) == 1
    evidence = answer["data_evidence"][0]
    assert evidence["tool"] == "query_metrics"
    assert evidence["params"] == {"start": day, "end": day,
                                  "store_id": "S02", "product_id": "P06"}
    assert evidence["result"]["qty"] == qty


def test_replacement_alias_exact_date_excludes_adjacent_row(replacement):
    service, client, source = replacement
    with sqlite3.connect(source) as conn:
        rows = conn.execute("SELECT date,qty,amount FROM sales ORDER BY date,order_id").fetchall()
    assert rows == [("2026-06-18", "2", "-60.00"),
                    ("2026-06-18", "9", "210.00"),
                    ("2026-07-01", "5", "100.00")]
    assert 9 - 2 == 7
    exact = service.metrics_summary("2026-06-18", "2026-06-18", "S02", "P06")
    assert exact["qty"] == 7
    request, answer, trace = ask(client, service, "scope", "S02 6月18日红岩饭销量是多少？")
    assert_exact_day(answer, "2026-06-18", 7)
    plan = next(step["detail"] for step in trace["steps"] if step["step"] == "plan")
    assert plan["window"] == ["2026-06-18", "2026-06-18"]
    if evidence_dir := os.environ.get("G304_DATE_EVIDENCE_DIR"):
        output = Path(evidence_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "exact-day-http.json").write_text(json.dumps({
            "independent_sql_rows": rows,
            "independent_expected_qty": 7,
            "metrics_exact_day": exact,
            "request": request, "response": answer, "trace": trace,
        }, ensure_ascii=False, indent=2) + "\n")


@pytest.mark.parametrize("question,day,qty", [
    ("S02 6 月 18 日 红岩饭销量是多少？", "2026-06-18", 7),
    ("S02 6月18号牛肉poke销量是多少？", "2026-06-18", 7),
    ("S02六月十八日红岩饭销量是多少？", "2026-06-18", 7),
    ("S02 7月1日红岩饭销量是多少？", "2026-07-01", 5),
])
def test_spacing_adjacent_entities_and_other_day(replacement, question, day, qty):
    service, client, _ = replacement
    _, answer, _ = ask(client, service, "variant", question)
    assert_exact_day(answer, day, qty)


def test_explicit_day_overrides_prior_session_and_attached_trend(replacement):
    service, client, _ = replacement
    _, prior, _ = ask(client, service, "follow", "S02 7月1日红岩饭销量是多少？")
    assert_exact_day(prior, "2026-07-01", 5)
    _, follow, _ = ask(client, service, "follow", "那6月18日呢？")
    assert_exact_day(follow, "2026-06-18", 7)
    attachment = {"type": "daily_trend", "start": "2026-07-01", "end": "2026-07-01",
                  "store_id": "S02", "metric": "net_revenue"}
    _, attached, trace = ask(client, service, "trend", "S02 6月18日红岩饭销量是多少？", attachment)
    assert_exact_day(attached, "2026-06-18", 7)
    resolved = next(step["detail"] for step in trace["steps"] if step["step"] == "context_resolution")
    assert resolved["effective"]["start"] == "2026-06-18"


def test_no_explicit_day_keeps_bounded_data_period(replacement):
    service, client, _ = replacement
    _, answer, _ = ask(client, service, "whole", "S02 红岩饭销量是多少？")
    assert answer["answer_type"] == "data"
    assert answer["data_evidence"][0]["params"]["start"] == "2026-06-18"
    assert answer["data_evidence"][0]["params"]["end"] == "2026-07-01"
    assert answer["data_evidence"][0]["result"]["qty"] == 12


def test_unseparated_unknown_store_id_is_not_split(replacement):
    service, client, _ = replacement
    _, answer, trace = ask(client, service, "ambiguous", "S026月18日红岩饭销量是多少？")
    assert answer["answer_type"] == "refusal" and answer["data_evidence"] == []
    plan = next(step["detail"] for step in trace["steps"] if step["step"] == "plan")
    assert plan["kind"] == "unknown_entity"
    assert service.catalog.find_store("S026月18日红岩饭销量是多少？") == (None, "S026")


def test_date_parser_excludes_store_suffix_from_month():
    for question, expected in [
        ("S02 6月18日红岩饭销量是多少？", "2026-06-18"),
        ("S01 2月8日牛肉poke销量是多少？", "2026-02-08"),
    ]:
        spec = parse_time(question, date(2026, 9, 1))
        assert spec.windows == [(expected, expected)]


def test_controlled_live_cannot_expand_explicit_day(replacement, monkeypatch):
    service, client, _ = replacement
    service.settings = replace(service.settings, llm_base_url="http://controlled",
                               llm_api_key="local-test-only", llm_model="controlled")
    broad = {"start": "2026-06-18", "end": "2026-07-01",
             "store_id": "S02", "product_id": "P06"}
    exact = {**broad, "end": "2026-06-18"}
    rounds = []

    def tool_reply(call_id, params):
        call = {"id": call_id, "type": "function", "function": {
            "name": "query_metrics", "arguments": json.dumps(params)}}
        return LLMReply({"role": "assistant", "content": "", "tool_calls": [call]},
                        "tool_calls", "", [call], 0)

    def controlled(self, messages, tools=None, **kwargs):
        index = len(rounds)
        rounds.append(index)
        if index == 0:
            return tool_reply("broad", broad)
        result = json.loads(messages[-1]["content"])
        if index == 1:
            assert result["call_id"] == "broad" and "error" in result["result"]
            return tool_reply("exact", exact)
        assert result["call_id"] == "exact" and result["result"]["qty"] == 7
        content = json.dumps({"answer_type": "data", "results": [
            {"call_id": "exact", "metric": "qty"}]})
        return LLMReply({"role": "assistant", "content": content}, "stop", content, [], 0)

    monkeypatch.setattr(LLMClient, "chat_with_retry", controlled)
    _, answer, trace = ask(client, service, "live-day", "S02 6月18日红岩饭销量是多少？")
    assert_exact_day(answer, "2026-06-18", 7)
    tools = [step["detail"] for step in trace["steps"] if step["step"] == "tool"]
    assert len(tools) == 2
    assert tools[0]["params"] == broad and "error" in tools[0]["result"]
    assert tools[1]["params"] == exact and tools[1]["result"]["qty"] == 7
    assert any(step["step"] == "explicit_data_scope" for step in trace["steps"])


@pytest.mark.parametrize("question,tool_name,params", [
    ("S02 红岩饭销量是多少？", "query_metrics",
     {"start": "2026-06-18", "end": "2026-07-01", "store_id": "S02", "product_id": "P06"}),
    ("S02 6月18日和7月1日红岩饭销量差多少？", "compare_periods",
     {"start_a": "2026-06-18", "end_a": "2026-06-18",
      "start_b": "2026-07-01", "end_b": "2026-07-01",
      "store_id": "S02", "product_id": "P06"}),
])
def test_controlled_live_retains_undated_and_comparison_tools(replacement, monkeypatch,
                                                              question, tool_name, params):
    service, client, _ = replacement
    service.settings = replace(service.settings, llm_base_url="http://controlled",
                               llm_api_key="local-test-only", llm_model="controlled")
    calls = []

    def controlled(self, messages, tools=None, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            call = {"id": "allowed", "type": "function", "function": {
                "name": tool_name, "arguments": json.dumps(params)}}
            return LLMReply({"role": "assistant", "content": "", "tool_calls": [call]},
                            "tool_calls", "", [call], 0)
        result = json.loads(messages[-1]["content"])
        assert result["call_id"] == "allowed" and "error" not in result["result"]
        content = json.dumps({"answer_type": "data", "results": [
            {"call_id": "allowed", "metric": "qty"}]})
        return LLMReply({"role": "assistant", "content": content}, "stop", content, [], 0)

    monkeypatch.setattr(LLMClient, "chat_with_retry", controlled)
    _, answer, trace = ask(client, service, "allowed-live", question)
    assert answer["answer_type"] == "data"
    tools = [step["detail"] for step in trace["steps"] if step["step"] == "tool"]
    assert len(tools) == 1 and tools[0]["tool"] == tool_name
    assert tools[0]["params"] == params
    assert tools[0]["result"] == service.run_tool(tool_name, params)
    assert not any(step["step"] == "explicit_data_scope" for step in trace["steps"])
