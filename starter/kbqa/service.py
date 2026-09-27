"""把各个部件接起来：规划、取数、检索、作答。"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional
from datetime import date

from .answerer import Answerer
from .schemas import Answer
from .cleaning import build_clean_db
from .docfacts import DocFacts
from .config import Settings, load_settings
from .entities import Catalog
from .index import load_index
from .live import LiveEngine
from .llm import LLMClient, LLMError
from .planner import Planner
from .retriever import Retriever
from .sessions import SessionStore
from .toolspec import TOOL_NAMES, TOOLS
from .tools import DataTools
from .trace import Trace, TraceStore
from .redaction import redact
from .trend_context import validate as validate_trend_context, resolve as resolve_trend_context

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_INT_PARAMS = {"top_k", "limit"}


class Service:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or load_settings()
        self.sessions = SessionStore()
        self.traces = TraceStore()
        self.rebuild(only_if_missing=True)

    # -- 启动与重建 -------------------------------------------------------------

    def rebuild(self, only_if_missing: bool = False) -> None:
        settings = self.settings
        if not only_if_missing or not settings.clean_db.exists():
            build_clean_db(settings.source_db, settings.clean_db)
        self.tools = DataTools(settings.clean_db)
        self.index = load_index(settings.kb_dir, settings.index_path, rebuild=not only_if_missing)
        self.catalog = Catalog(
            stores=self.tools.stores(), products=self.tools.products(), aliases=self.index.aliases
        )
        self.retriever = Retriever(self.index, settings.today, self.catalog)
        self.data_period = self.tools.data_period()
        self.facts = DocFacts(self.index)
        self.answerer = Answerer(
            self.tools, self.retriever, self.catalog, settings.today, self.data_period, self.facts
        )
        self.planner = Planner(self.catalog, settings.today, self.data_period, self._scout)

    def _scout(self, text: str) -> tuple[float, float]:
        """给一句话探底：它的词在知识库里有多少、检索最高分多少。

        越界判断只看这两个数，不看话题词表：知识库真讲这件事就一定照答。
        """
        result = self.retriever.search(text, top_k=1)
        return self.facts.vocab_coverage(text), (result.hits[0].score if result.hits else 0.0)

    # -- 只读接口 ---------------------------------------------------------------

    def health(self) -> dict:
        report = self.tools.cleaning_report()
        return {
            "status": "ok",
            "llm_mode": self.settings.llm_mode,
            "kb_docs": len(self.index.docs_meta),
            "kb_chunks": len(self.index.chunks),
            "valid_sales_rows": self.tools.valid_sales_rows(),
            "today": self.settings.today.isoformat(),
            "data_period": self.data_period,
            "cleaning_report": report,
            "index_key": self.index.key[:12],
            "kb_warnings": self.index.warnings,
        }

    def metrics_summary(self, start: str, end: str, store_id=None, product_id=None) -> dict:
        return self.tools.query_metrics(start, end, store_id, product_id)

    def metrics_daily(self, start: str, end: str, store_id=None, product_id=None) -> dict:
        return self.tools.daily_metrics(start, end, store_id, product_id)

    def metrics_top_products(self, start: str, end: str, store_id=None) -> dict:
        return self.tools.top_products(start, end, store_id)

    def retrieve(self, query: str, top_k: int = 5) -> dict:
        """契约 §4：片段够就恰好给 top_k 条，不够才少给。

        `top_k` 大于索引里的片段总数时按总数封顶——这正是契约允许少给的那种情况。
        """
        wanted = max(1, min(int(top_k or 5), len(self.index.chunks) or 1))
        result = self.retriever.search(query or "", top_k=wanted)
        return {"results": [hit.as_result() for hit in result.hits], "diagnostics": result.as_trace()}

    # -- 工具执行（live 模式下由模型驱动） ---------------------------------------

    def run_tool(self, name: str, params: dict, *, plan=None) -> dict:
        if name not in TOOL_NAMES:
            return {"error": "没有这个工具：%s，可用工具：%s" % (name, "、".join(TOOL_NAMES))}
        schema = next(
            tool["function"]["parameters"] for tool in TOOLS if tool["function"]["name"] == name
        )
        if not isinstance(params, dict):
            return {"error": "工具参数必须是 JSON 对象"}
        cleaned: dict[str, Any] = {}
        for key, value in params.items():
            if key not in schema["properties"]:
                return {"error": "未声明的参数：%s" % key}
            if key in _INT_PARAMS:
                maximum = 10
                if type(value) is not int or not 1 <= value <= maximum:
                    return {"error": "参数 %s 必须是 1 至 %s 的整数" % (key, maximum)}
                cleaned[key] = value
                continue
            if value is None and key not in schema.get("required", []):
                continue
            if not isinstance(value, str) or not value.strip():
                return {"error": "参数 %s 必须是非空字符串" % key}
            text = value.strip()
            if key.startswith(("start", "end")) or key == "date":
                try:
                    if not _ISO_DATE.fullmatch(text):
                        raise ValueError()
                    date.fromisoformat(text)
                except ValueError:
                    return {"error": "参数 %s 必须是有效 YYYY-MM-DD 日期" % key}
            if key in ("store_id", "product_id"):
                text = text.upper()
                valid = self.catalog.store_ids() if key == "store_id" else [p["product_id"] for p in self.catalog.products]
                if text not in valid:
                    return {"error": "未知%s：%s" % (key, text)}
            cleaned[key] = text
        for key in schema.get("required", []):
            if key not in cleaned:
                return {"error": "缺少必填参数 %s" % key}
        for suffix in ("", "_a", "_b"):
            start, end = cleaned.get("start" + suffix), cleaned.get("end" + suffix)
            if start and end and (start > end or (date.fromisoformat(end) - date.fromisoformat(start)).days > 366):
                return {"error": "日期区间必须顺序正确且不超过 367 天"}
            if start and self.data_period["start"] and start < self.data_period["start"] or end and self.data_period["end"] and end > self.data_period["end"]:
                return {"error": "查询区间超出已有数据范围"}
        try:
            if name == "search_kb":
                search = self.retriever.search(cleaned["query"], top_k=cleaned.get("top_k", 5),
                    as_of=(plan.as_of or self.settings.today) if plan else None,
                    store_id=plan.store_id if plan else None, year=plan.year if plan else None,
                    historical=bool(plan.slots.get("historical")) if plan else None)
                from .document_evidence import DocumentEvidence
                pool = DocumentEvidence(self.facts, search,
                    self.answerer.answerable_hits(plan, search, limit=10) if plan else None)
                return {"results": [h.as_result() for h in search.ranked],
                        "evidence": pool.public(), "scope": search.scope,
                        "diagnostics": search.as_trace(), "rejected": pool.rejected}
            return getattr(self.tools, name)(**cleaned)
        except (TypeError, ValueError) as exc:
            return {"error": "工具 %s 执行失败：%s" % (name, exc)}

    # -- 问答 -------------------------------------------------------------------

    def chat(self, session_id: Optional[str], question: str, context: Any = None) -> dict:
        trace = Trace(
            trace_id=self.traces.new_id(self.settings.today.isoformat()),
            question=question or "",
            session_id=session_id,
            secrets=(self.settings.llm_api_key,),
        )
        trace.step("request", {"session_id": session_id, "question": question, "context": context})
        with self.sessions.ordered(session_id) as acquired:
            if acquired:
                answer = self._answer(trace, session_id, question or "", context)
            else:
                trace.step("session_busy", {"wait_limit_ms": 250, "history_changed": False})
                answer = Answer(
                    answer="当前对话正在处理上一条问题，请稍后重试。",
                    answer_type="refusal",
                )
            trace.step("response", {"answer_type": answer.answer_type, "notes": answer.notes})
            self.traces.save(trace)
        payload = {
            "answer": answer.answer,
            "answer_type": answer.answer_type,
            "citations": answer.citations,
            "data_evidence": answer.data_evidence,
            "trace_id": trace.trace_id,
        }
        return redact(payload, (self.settings.llm_api_key,))

    def _answer(self, trace: Trace, session_id: Optional[str], question: str, context: Any = None) -> Answer:
        try:
            reference, problem = validate_trend_context(context, self.catalog, self.data_period)
            trace.step("context_validation", {"valid": problem is None, "reason": problem, "reference": reference})
            if problem:
                self.sessions.forget(session_id)
                trace.step("session_context_cleared", {"reason": "invalid_trend_reference"})
                return Answer(answer=problem, answer_type="refusal")
            if not question.strip():
                return Answer(answer="没有收到问题内容，请再说一次。", answer_type="clarify")
            history = self.sessions.history(session_id)
            started = time.perf_counter()
            plan = self.planner.plan(question, history)
            trace.step("session_context", {
                "history_size": len(history),
                "source_questions": [turn["question"] for turn in history],
                "source_conditions": [turn.get("slots", {}) for turn in history],
                "raw_question": question,
                "standalone_question": plan.standalone,
                "inherited": plan.standalone != question,
                "effective_conditions": plan.as_trace(),
            })
            effective = None
            # Keep G3-01's live semantic route for heuristic out_of_scope:
            # a business request can have an unrelated preamble. Only hard
            # safety/identity failures and required clarifications stop here.
            hard_stop = {"prohibited_request", "need_context", "need_month", "unknown_entity", "out_of_period"}
            if reference and plan.kind not in hard_stop:
                resolution = resolve_trend_context(plan, question, reference, self.catalog,
                                                   self.settings.today, self.data_period)
                trace.step("context_resolution", resolution)
                effective = resolution["effective"]
            elif reference and plan.kind in {"unknown_entity", "out_of_period"}:
                plan.slots["trend_reference_rejection"] = True
            trace.step("plan", plan.as_trace(), started=started)
            # Planner may leave a natural follow-up untouched; the model still
            # needs accepted prior questions to interpret omitted conditions.
            # An unrelated request after clarification must not inherit that
            # unresolved question merely because it shares a session ID.
            clarification_reset = bool(history and history[-1].get("answer_type") == "clarify"
                                       and plan.standalone == question)
            context_history = [] if clarification_reset else history
            trace.step("model_context", {"prompt_history_size": min(3, len(context_history)),
                                         "clarification_reset": clarification_reset})
            # Preserve the original three-argument execution seam for ordinary
            # chat and diagnostic writers. Only a resolved trend adds scope.
            answer = (self._run_engine(plan, trace, context_history, effective)
                      if effective else self._run_engine(plan, trace, context_history))
            if not self.settings.live:
                for item in answer.data_evidence:
                    trace.step("tool", item)
            # Failed/refused answers are not factual context for another turn.
            # A neutral clarification remains available so its answer can be
            # completed, but its prose is never treated as evidence.
            if answer.answer_type in {"data", "doc", "hybrid", "clarify"}:
                self.sessions.append(
                    session_id,
                    redact({
                        "question": question,
                        "standalone": plan.standalone,
                        "slots": plan.slots,
                        "source_titles": [self.index.docs_meta.get(c.get("doc_id"), {}).get("title")
                                          for c in answer.citations
                                          if self.index.docs_meta.get(c.get("doc_id"), {}).get("title")],
                        "answer": answer.answer if answer.answer_type != "clarify" else "",
                        "answer_type": answer.answer_type,
                    }, (self.settings.llm_api_key,)),
                )
            elif answer.answer_type == "refusal":
                # A refusal may be a new topic or a failed tool. Keep neither
                # its unsupported facts nor an older unrelated topic alive.
                self.sessions.forget(session_id)
                trace.step("session_context_cleared", {"reason": "refusal"})
            return answer
        except Exception as exc:  # noqa: BLE001 - preserve the chat response contract
            trace.error("answer", exc)
            self.sessions.forget(session_id)
            trace.step("session_context_cleared", {"reason": "answer_error"})
            # Never attach raw exc_info: logging formatters would recreate the
            # unsanitized cause/context chain after our diagnostic scrub.
            logging.getLogger(__name__).error("chat failed trace_id=%s\n%s",
                redact(trace.trace_id, trace.secrets), trace.errors[-1]["traceback"])
            return Answer(
                answer="抱歉，我暂时无法回答。",
                answer_type="refusal",
            )

    def _run_engine(self, plan, trace: Trace, history: list[dict], effective: dict | None = None) -> Answer:
        if (not self.settings.live or
                plan.kind in {"prohibited_request", "need_context", "need_month",
                              "trend_ambiguous_time", "trend_invalid_condition"} or
                plan.slots.get("trend_reference_rejection")):
            started = time.perf_counter()
            answer = self.answerer.answer(plan, trace)
            trace.step("answer_mock", {"answer_type": answer.answer_type}, started=started)
            return answer
        client = LLMClient(
            self.settings.llm_base_url,
            self.settings.llm_api_key,
            self.settings.llm_model,
            timeout=self.settings.llm_timeout,
        )
        def scoped_tool(name, params, *, plan=plan):
            # The document executor supplies its original Plan as a private
            # keyword. Preserve it through the trend scope wrapper as well.
            return self._run_scoped_tool(name, params, effective, plan)

        engine = LiveEngine(
            client,
            self.answerer,
            scoped_tool if effective else self.run_tool,
            self.settings.today.isoformat(),
            self.data_period,
            budget=self.settings.chat_budget,
        )
        started = time.perf_counter()
        try:
            answer = engine.answer(plan, trace, history)
            trace.step("answer_live", {"answer_type": answer.answer_type}, started=started)
            return answer
        except LLMError as exc:
            trace.error("llm", exc)
            trace.step("answer_live_failed", {"kind": exc.kind, "detail": exc.detail}, started=started)
            return Answer(
                answer="模型服务这次没有正常返回（%s），为了不给出没有依据的数字，这个问题先不回答。"
                "可以稍后重试；失败的真实原因记在 trace 里。" % _reason_cn(exc),
                answer_type="refusal",
                notes=["live 模式失败：%s" % exc.detail],
            )

    def _run_scoped_tool(self, name: str, params: dict, effective: dict, plan) -> dict:
        """A model cannot silently exchange the resolved reference scope for another one."""
        if name not in TOOL_NAMES or not isinstance(params, dict):
            return self.run_tool(name, params)
        if name != "search_kb":
            if name == "compare_periods":
                required = {
                    "start_a": plan.window[0], "end_a": plan.window[1],
                    "store_id": effective["store_id"],
                    "product_id": effective.get("product_id"),
                }
                if plan.compare_window:
                    required.update(start_b=plan.compare_window[0], end_b=plan.compare_window[1])
                if not plan.compare_window or any(params.get(key) != value for key, value in required.items()):
                    return {"error": "比较查询与文字明确指定的有效条件不一致"}
                return self.run_tool(name, params)
            if plan.compare_window:
                return {"error": "明确比较两个区间时必须查询两个区间"}
            if params.get("start") != effective["start"] or params.get("end") != effective["end"]:
                return {"error": "查询日期与已验证的有效条件不一致"}
            properties = next(tool["function"]["parameters"]["properties"] for tool in TOOLS if tool["function"]["name"] == name)
            if "store_id" not in properties:
                if effective["store_id"] is not None:
                    return {"error": "此工具不能按引用门店查询"}
            elif params.get("store_id") != effective["store_id"]:
                return {"error": "查询门店与已验证的有效条件不一致"}
            if "product_id" not in properties:
                if effective.get("product_id") is not None:
                    return {"error": "此工具不能按问题中的商品查询"}
            elif params.get("product_id") != effective.get("product_id"):
                return {"error": "查询商品与本轮有效条件不一致"}
        return self.run_tool(name, params, plan=plan) if name == "search_kb" else self.run_tool(name, params)

    # -- trace ------------------------------------------------------------------

    def get_trace(self, trace_id: str) -> Optional[dict]:
        return self.traces.get(trace_id)


def _reason_cn(exc: LLMError) -> str:
    mapping = {
        "timeout": "调用超时",
        "http_error": "接口返回错误码 %s" % (exc.status or ""),
        "empty_content": "返回了空回答",
        "length": "输出额度被思考耗尽",
        "content_filter": "被内容过滤拦截",
        "insufficient_system_resource": "服务端资源不足",
        "aborted": "请求被中止",
        "bad_tool_args": "工具参数无法解析",
        "bad_json": "返回的不是合法 JSON",
        "budget": "整体耗时接近时限",
        "transport": "网络异常",
        "tool_loop": "工具调用没有收敛",
        "tool_failure": "工具执行失败",
        "clarification_binding": "澄清结构无效",
        "mixed_binding": "混合证据或计算关系无法核验",
    }
    return mapping.get(exc.kind, exc.kind)
