"""Validate an explicit daily-trend reference and resolve its scope for one turn."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from . import entities as E
from .timeparse import parse_time
from .tokenizer import normalise

FIELDS = {"type", "start", "end", "store_id", "metric"}
AMBIGUOUS = re.compile(r"这一周|这周|本周|上周|那一周|这一月|这月|那个月")


def validate(raw: Any, catalog, period: dict) -> tuple[dict | None, str | None]:
    if raw is None:
        return None, None
    if not isinstance(raw, dict) or set(raw) != FIELDS:
        return None, "趋势引用字段不完整或包含未允许字段。"
    if raw["type"] != "daily_trend" or raw["metric"] != "net_revenue":
        return None, "只支持每日净营业额趋势引用。"
    start, end = raw["start"], raw["end"]
    try:
        if any(not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) for value in (start, end)):
            raise ValueError()
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        if first > last or (last - first).days > 366:
            raise ValueError()
    except ValueError:
        return None, "趋势引用日期必须是有效、正序且不超过 367 天的闭区间。"
    if start < (period["start"] or "") or end > (period["end"] or ""):
        return None, "趋势引用超出当前数据日期范围。"
    store = raw["store_id"]
    if store is not None and (not isinstance(store, str) or store not in catalog.store_ids()):
        return None, "趋势引用门店不存在。"
    return dict(raw), None


def _stop(plan, kind: str, reason: str, answer: str) -> dict:
    plan.intent = "clarify" if kind == "trend_ambiguous_time" else "refusal"
    plan.kind, plan.refusal = kind, answer
    plan.notes.append("趋势引用条件未通过验证：%s" % reason)
    return {"effective": None,
            ("clarification" if plan.intent == "clarify" else "rejection"): reason}


def _product_in_question(question: str, catalog) -> tuple[str | None, str | None]:
    product, unknown = catalog.find_product(question)
    if product or unknown:
        return product, unknown
    # Catalog's word-boundary matcher misses codes immediately before Chinese
    # text. Recognise only the same code shape and validate against the catalog.
    codes = re.findall(r"(?<![a-z0-9])p\d{1,2}(?![a-z0-9])", normalise(question))
    if not codes:
        return None, None
    code = codes[0].upper()
    return (code, None) if code in {p["product_id"] for p in catalog.products} else (None, code)


def resolve(plan, question: str, context: dict, catalog, today: date, period: dict) -> dict:
    """Resolve every explicit slot, including after an early heuristic planner exit."""
    spec = parse_time(question, today)
    explicit_store, unknown_store = catalog.find_store(question)
    explicit_product, unknown_product = _product_in_question(question, catalog)
    explicit_metric = E.find_metric(question)
    if unknown_store:
        return _stop(plan, "trend_invalid_condition", "unknown_store", "问题中的门店 %s 不存在，请核对门店编号。" % unknown_store)
    if unknown_product:
        return _stop(plan, "trend_invalid_condition", "unknown_product", "问题中的商品 %s 不存在，请核对商品编号。" % unknown_product)

    if (AMBIGUOUS.search(question) or any(word in question for word in ("最近", "近期", "至今"))) and not spec.windows:
        return _stop(plan, "trend_ambiguous_time", "unanchored_relative_period",
                     "请说明具体是哪几天，或明确说按引用的整个趋势区间查询。")
    if spec.first_month and not spec.windows:
        return _stop(plan, "trend_ambiguous_time", "first_month_without_window",
                     "请明确首月的具体日期区间，再使用这张趋势引用提问。")

    source: dict[str, str] = {}
    if len(spec.windows) > 2 or (len(spec.windows) == 2 and not
            (E.has_any(question, E.TREND_WORDS) or "比较" in question)):
        return _stop(plan, "trend_ambiguous_time", "multiple_periods_without_comparison",
                     "问题包含多个日期区间，请明确是否要比较这两个区间。")
    if spec.windows:
        plan.window = spec.windows[0]
        plan.compare_window = spec.windows[1] if len(spec.windows) == 2 else None
        source["window"] = "question"
        if plan.compare_window:
            source["compare_window"] = "question"
    elif "全部时间" in question:
        plan.window = (period["start"], period["end"])
        plan.compare_window = None
        source["window"] = "question"
    elif spec.relative_now:
        plan.window = (today.isoformat(), today.isoformat())
        plan.compare_window = None
        source["window"] = "question"
    else:
        plan.window = (context["start"], context["end"])
        plan.compare_window = None
        source["window"] = "reference"

    for window in (plan.window, plan.compare_window):
        if not window:
            continue
        start, end = window
        if (date.fromisoformat(end) - date.fromisoformat(start)).days > 366:
            return _stop(plan, "trend_invalid_condition", "window_too_long",
                         "明确指定的日期区间超过 367 天，请缩小范围。")
        if start < period["start"] or end > period["end"]:
            return _stop(plan, "trend_invalid_condition", "out_of_period",
                         "明确指定的 %s 至 %s 超出已有数据范围 %s 至 %s，请重新指定日期。" %
                         (start, end, period["start"], period["end"]))

    all_stores = any(word in question for word in ("全部门店", "所有门店", "各门店"))
    if all_stores and explicit_store:
        return _stop(plan, "trend_ambiguous_time", "conflicting_store_scope",
                     "请明确查询指定门店还是全部门店。")
    plan.store_id = None if all_stores else explicit_store or context["store_id"]
    source["store_id"] = "question" if explicit_store or all_stores else "reference"
    plan.metric = explicit_metric or context["metric"]
    source["metric"] = "question" if explicit_metric else "reference"
    if explicit_product:
        plan.product_id = explicit_product
        source["product_id"] = "question"

    plan.slots.update({"window": plan.window, "compare_window": plan.compare_window,
                       "store_id": plan.store_id, "product_id": plan.product_id,
                       "metric": plan.metric})
    effective = {"start": plan.window[0], "end": plan.window[1],
                 "store_id": plan.store_id, "metric": plan.metric}
    if plan.compare_window:
        effective["compare_window"] = list(plan.compare_window)
    if explicit_product:
        effective["product_id"] = explicit_product
    plan.notes.append("趋势引用条件来源：%s；有效条件：%s" % (source, effective))
    plan.slots["context_effective"] = effective
    return {"effective": effective, "source": source,
            "overrides": [key for key, origin in source.items() if origin == "question"]}
