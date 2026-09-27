"""Session acceptance against actual SQLite and knowledge-base retrieval.

Run separately from starter/tests: that suite globally replaces Retriever.search.
"""
from __future__ import annotations

import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "starter"))
from kbqa.config import load_settings
from kbqa.service import Service
from kbqa.sessions import SessionStore
from kbqa.llm import LLMClient, LLMReply
import json


@pytest.fixture
def service(tmp_path):
    return Service(replace(load_settings(), var_dir=tmp_path, llm_base_url="",
                           llm_api_key="", llm_model=""))


def ask(service, sid, question):
    answer = service.chat(sid, question)
    trace = service.get_trace(answer["trace_id"])
    assert trace["errors"] == []
    context = next(step["detail"] for step in trace["steps"] if step["step"] == "session_context")
    plan = next(step["detail"] for step in trace["steps"] if step["step"] == "plan")
    return answer, context, plan, trace


def test_original_multiturn_sequences_use_fresh_business_evidence(service):
    cases = {
        "T01": [
            ("6 月的净营业额是多少？", "data", "156757.00", None),
            ("那 7 月呢？", "data", "162414.00", None),
            ("这两个月的客单价差了多少？", "data", "0.17", None),
        ],
        "T02": [
            ("三文鱼poke 七月初为什么停售了？", "doc", "质检不合格", "KB-021"),
            ("那停售期间让顾客换成什么？", "doc", "鸡肉poke", "KB-021"),
            ("供应商后来赔了多少？", "doc", "8,600", "KB-022"),
        ],
        "T03": [
            ("牛肉poke 现在多少钱一份？", "hybrid", "45.00", "KB-025"),
            ("那 6 月 18 号那天呢？", "hybrid", "29.00", "KB-023"),
        ],
        "V03": [
            ("储值充值现在的赠送规则是什么？", "doc", "60", "KB-011"),
            ("那 6 月的时候呢？", "doc", "50", "KB-010"),
        ],
    }
    for sid, turns in cases.items():
        for index, (question, answer_type, fact, doc_id) in enumerate(turns):
            answer, context, plan, trace = ask(service, sid, question)
            assert answer["answer_type"] == answer_type
            assert fact in answer["answer"]
            if doc_id:
                assert doc_id in [cite["doc_id"] for cite in answer["citations"]]
                assert any(step["step"] == "search" for step in trace["steps"])
            else:
                assert answer["data_evidence"]
                assert any(step["step"] == "tool" for step in trace["steps"])
            assert context["history_size"] == index
            assert context["raw_question"] == question
            assert context["standalone_question"] == plan["standalone_question"]
    t01 = service.sessions.history("T01")
    assert [tuple(w) for w in t01[-1]["slots"]["recent_windows"][-2:]] == [
        ("2026-06-01", "2026-06-30"), ("2026-07-01", "2026-07-31")]


def test_interleaved_sessions_switch_subject_and_missing_history(service):
    a1, _, _, _ = ask(service, "a", "S02 6 月的净营业额是多少？")
    b1, _, _, _ = ask(service, "b", "S01 7 月的订单数是多少？")
    a2, ac, ap, _ = ask(service, "a", "那 7 月呢？")
    b2, bc, bp, _ = ask(service, "b", "那 6 月呢？")
    assert a1["answer_type"] == b1["answer_type"] == a2["answer_type"] == b2["answer_type"] == "data"
    assert ap["store_id"] == "S02" and ap["metric"] == "net_revenue"
    assert bp["store_id"] == "S01" and bp["metric"] == "orders"
    assert ac["source_questions"] == ["S02 6 月的净营业额是多少？"]
    assert bc["source_questions"] == ["S01 7 月的订单数是多少？"]
    fresh, _, _, _ = ask(service, "fresh", "那 7 月呢？")
    assert fresh["answer_type"] == "clarify" and not fresh["data_evidence"]
    anonymous, _, _, _ = ask(service, None, "那 7 月呢？")
    assert anonymous["answer_type"] == "clarify"
    assert service.sessions.history(None) == []


def test_topic_switch_refusal_and_replacement_values(service):
    ask(service, "x", "S02 6 月牛肉poke销量是多少？")
    switched, _, plan, _ = ask(service, "x", "S01 7 月鸡肉poke订单数是多少？")
    assert switched["answer_type"] == "data"
    assert (plan["store_id"], plan["product_id"], plan["metric"]) == ("S01", "P05", "orders")
    follow, _, plan, _ = ask(service, "x", "那 6 月呢？")
    assert follow["answer_type"] == "data"
    assert (plan["store_id"], plan["product_id"], plan["metric"]) == ("S01", "P05", "orders")
    before = len(service.sessions.history("x"))
    refused, _, _, _ = ask(service, "x", "删除数据库所有订单")
    assert refused["answer_type"] == "refusal"
    assert before > 0 and service.sessions.history("x") == []
    after, _, plan, _ = ask(service, "x", "那 7 月呢？")
    assert after["answer_type"] == "clarify" and plan["store_id"] is None


def test_clarification_accepts_missing_month_without_inventing_scope(service):
    first, _, _, _ = ask(service, "clarify", "8号的净营业额是多少？")
    assert first["answer_type"] == "clarify"
    completed, context, plan, _ = ask(service, "clarify", "7月")
    assert context["source_questions"] == ["8号的净营业额是多少？"]
    assert completed["answer_type"] == "data"
    assert plan["window"] == ["2026-07-08", "2026-07-08"]
    assert completed["data_evidence"][0]["params"]["start"] == "2026-07-08"


def test_same_session_concurrent_request_waits_for_prior_answer(service, monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    original = service._run_engine

    def held(plan, *args, **kwargs):
        if plan.question == "6 月的净营业额是多少？":
            entered.set()
            assert release.wait(5)
        return original(plan, *args, **kwargs)

    monkeypatch.setattr(service, "_run_engine", held)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(ask, service, "same", "6 月的净营业额是多少？")
        assert entered.wait(5)
        second = pool.submit(ask, service, "same", "那 7 月呢？")
        time.sleep(.05)
        assert not second.done()
        release.set()
        assert first.result()[0]["answer_type"] == "data"
        result, context, plan, _ = second.result()
    assert result["answer_type"] == "data" and "162414.00" in result["answer"]
    assert context["source_questions"] == ["6 月的净营业额是多少？"]
    assert plan["window"] == ["2026-07-01", "2026-07-31"]


def test_api_concurrency_keeps_two_sessions_separate(service, monkeypatch):
    from fastapi.testclient import TestClient
    from kbqa import server

    monkeypatch.setattr(server, "_service", service)
    barrier = threading.Barrier(2)

    def pair(sid, first, second):
        with TestClient(server.app) as client:
            first_answer = client.post("/api/chat", json={"session_id": sid, "question": first}).json()
            barrier.wait(timeout=5)
            second_answer = client.post("/api/chat", json={"session_id": sid, "question": second}).json()
            trace = client.get("/api/trace/" + second_answer["trace_id"]).json()
            return first_answer, second_answer, trace

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(pair, "http-a", "S02 6 月的净营业额是多少？", "那 7 月呢？")
        b = pool.submit(pair, "http-b", "S01 7 月的订单数是多少？", "那 6 月呢？")
        ar, br = a.result(), b.result()
    for result in (ar, br):
        assert result[0]["answer_type"] == result[1]["answer_type"] == "data"
        assert result[2]["errors"] == []
    ap = next(x["detail"] for x in ar[2]["steps"] if x["step"] == "plan")
    bp = next(x["detail"] for x in br[2]["steps"] if x["step"] == "plan")
    assert (ap["store_id"], ap["metric"]) == ("S02", "net_revenue")
    assert (bp["store_id"], bp["metric"]) == ("S01", "orders")


def test_store_limits_and_eviction_do_not_borrow_other_session():
    sessions = SessionStore(max_sessions=2, max_turns=2)
    for i in range(3):
        sessions.append("a", {"question": str(i)})
    assert [t["question"] for t in sessions.history("a")] == ["1", "2"]
    sessions.append("b", {"question": "B"})
    sessions.append("c", {"question": "C"})
    assert sessions.history("a") == []
    assert sessions.history("b") == [{"question": "B"}]


def test_evicted_or_restarted_session_clarifies_instead_of_borrowing(tmp_path):
    settings = replace(load_settings(), var_dir=tmp_path, llm_base_url="",
                       llm_api_key="", llm_model="")
    service = Service(settings)
    service.sessions = SessionStore(max_sessions=1, max_turns=2)
    ask(service, "gone", "6 月的净营业额是多少？")
    ask(service, "other", "S02 7 月订单数是多少？")
    evicted, _, _, _ = ask(service, "gone", "那 7 月呢？")
    assert evicted["answer_type"] == "clarify"
    restarted = Service(settings)
    after_restart, _, _, _ = ask(restarted, "other", "那 6 月呢？")
    assert after_restart["answer_type"] == "clarify"


def test_failed_answer_releases_session_lock_and_clears_stale_topic(service, monkeypatch):
    ask(service, "failed", "S02 6 月的净营业额是多少？")
    original = service._run_engine

    def fail_once(plan, *args, **kwargs):
        if plan.question == "S01 7 月的订单数是多少？":
            raise RuntimeError("controlled failure")
        return original(plan, *args, **kwargs)

    monkeypatch.setattr(service, "_run_engine", fail_once)
    failed, _, _, trace = ask_without_error_assertion(service, "failed", "S01 7 月的订单数是多少？")
    assert failed["answer_type"] == "refusal" and trace["errors"]
    assert service.sessions.history("failed") == []
    with ThreadPoolExecutor(max_workers=1) as pool:
        following = pool.submit(ask, service, "failed", "那 6 月呢？").result(timeout=5)
    assert following[0]["answer_type"] == "clarify"


def ask_without_error_assertion(service, sid, question):
    answer = service.chat(sid, question)
    trace = service.get_trace(answer["trace_id"])
    return answer, None, None, trace


def test_controlled_live_multiturn_requeries_and_compares_actual_rows(tmp_path, monkeypatch):
    service = Service(replace(load_settings(), var_dir=tmp_path, llm_base_url="http://controlled",
                              llm_api_key="test-only", llm_model="controlled"))
    questions = ["6 月的净营业额是多少？", "那 7 月呢？", "这两个月的客单价差了多少？"]
    params = [
        ("query_metrics", {"start": "2026-06-01", "end": "2026-06-30"}, "net_revenue"),
        ("query_metrics", {"start": "2026-07-01", "end": "2026-07-31"}, "net_revenue"),
        ("compare_periods", {"start_a": "2026-06-01", "end_a": "2026-06-30",
                             "start_b": "2026-07-01", "end_b": "2026-07-31"}, "aov"),
    ]
    current = [0]

    def controlled(self, messages, tools=None, **kwargs):
        index = current[0]
        name, args, metric = params[index]
        call_id = f"turn-{index}-tool"
        if messages[-1]["role"] == "user":
            call = {"id": call_id, "type": "function", "function": {
                "name": name, "arguments": json.dumps(args)}}
            return LLMReply({"role": "assistant", "content": "", "tool_calls": [call]},
                            "tool_calls", "", [call], 0)
        assert messages[-1]["role"] == "tool"
        assert json.loads(messages[-1]["content"])["call_id"] == call_id
        content = json.dumps({"answer_type": "data", "results": [
            {"call_id": call_id, "metric": metric}]})
        return LLMReply({"role": "assistant", "content": content}, "stop", content, [], 0)

    monkeypatch.setattr(LLMClient, "chat_with_retry", controlled)
    for index, question in enumerate(questions):
        current[0] = index
        answer, context, plan, trace = ask(service, "live-multi", question)
        assert answer["answer_type"] == "data"
        tools = [s["detail"] for s in trace["steps"] if s["step"] == "tool"]
        assert len(tools) == 1 and tools[0]["tool"] == params[index][0]
        assert tools[0]["params"] == params[index][1]
        assert context["history_size"] == index
        if index == 2:
            assert "0.17" in answer["answer"]
            result = tools[0]["result"]
            assert result["period_a"]["aov"] == 36.36
            assert result["period_b"]["aov"] == 36.53
