"""Validate an explicit daily-trend reference and resolve its scope for one turn."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from . import entities as E
from .timeparse import parse_time

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


def resolve(plan, question: str, context: dict, catalog, today: date) -> dict:
    """Question slots take precedence; the reference fills only absent slots."""
    spec = parse_time(question, today)
    explicit_store, _ = catalog.find_store(question)
    explicit_metric = E.find_metric(question)
    if (AMBIGUOUS.search(question) or any(word in question for word in ("最近", "近期", "至今"))) and not spec.windows:
        plan.intent, plan.kind = "clarify", "trend_ambiguous_time"
        plan.refusal = "请说明“这一周”具体是哪几天，或明确说按引用的整个趋势区间查询。"
        return {"clarification": "unanchored_relative_period", "effective": None}
    source = {}
    question_window = bool(spec.windows or spec.relative_now or spec.first_month or "全部时间" in question)
    if not question_window:
        plan.window = (context["start"], context["end"])
        source["window"] = "reference"
    else:
        source["window"] = "question"
    all_stores = any(word in question for word in ("全部门店", "所有门店", "各门店"))
    if explicit_store or all_stores:
        if all_stores and not explicit_store:
            plan.store_id = None
        source["store_id"] = "question"
    else:
        plan.store_id = context["store_id"]
        source["store_id"] = "reference"
    if explicit_metric:
        source["metric"] = "question"
    else:
        plan.metric = context["metric"]
        source["metric"] = "reference"
    plan.slots.update({"window": plan.window, "store_id": plan.store_id, "metric": plan.metric})
    effective = {"start": plan.window[0], "end": plan.window[1], "store_id": plan.store_id, "metric": plan.metric}
    plan.notes.append("趋势引用条件来源：%s；有效条件：%s" % (source, effective))
    plan.slots["context_effective"] = effective
    return {"effective": effective, "source": source,
            "overrides": [key for key, origin in source.items() if origin == "question"]}
