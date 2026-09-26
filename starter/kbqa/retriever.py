"""检索：打分、按元数据过滤、取 top-k。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from .entities import Catalog, focus_kinds, wants_historical
from .docfacts import carries
from .timeparse import parse_time
from .index import BM25Index, load_index
from .tokenizer import content_tokens, normalise, tokenize

ALIAS_WEIGHT = 0.6
# Prefer a source passage carrying the requested fact shape over title-only matches.
SOURCE_FOCUS_BOOST = 1.5
#: 单字（“月”“日”“店”）在二元组的世界里基本是噪声，降权但不丢弃。
SINGLE_CHAR_WEIGHT = 0.3
YEAR_PENALTY = 0.25
FUTURE_PENALTY = 0.6
STORE_HINT_BOOST = 1.15
#: 问某个时间窗里“出了什么事”时，正好在这个窗里生效的文档最可能是答案。
WINDOW_BOOST = 1.8
#: 文档级先验：一篇文档整体命中得好，它的其它片段也更可能是答案所在。
#: 英文邮件里“赔了多少钱”的那一段本身不含任何中文查询词，靠的就是这一项。
DOC_PRIOR = 0.35
#: 别名词典本身不是答案，得压一压，不然它永远排第一。
ALIAS_DOC_PENALTY = 0.5
#: 周报、纪要里的数字是人工估的，问数字的时候给它们降点权。
ESTIMATE_DOC_PENALTY = 0.7
#: top-k 里一篇文档最多占一格：多留几篇不同的文档，比同一篇留两段有用；
#: 回答需要更多段落时另外按 doc_id 取。
MAX_CHUNKS_PER_DOC = 1


@dataclass
class Hit:
    doc_id: str
    chunk_id: str
    score: float
    text: str
    source_text: str
    meta: dict
    kind: str = "text"
    table_header: list[str] = field(default_factory=list)
    dropped_instructions: list[str] = field(default_factory=list)
    source_start: int = 0
    source_end: int = 0
    context_spans: list[dict] = field(default_factory=list)
    exclusion_reason: Optional[str] = None
    padded: bool = False
    """凑数补上的：契约 §4 要求恰好返回 top_k 条，但问答链路不会用它作答。"""

    def as_result(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "score": round(self.score, 4),
            "text": self.source_text,
            "retrieval_text": self.text,
            "source_start": self.source_start,
            "source_end": self.source_end,
            "context_spans": self.context_spans,
            "padded": self.padded,
            "evidence_eligible": not self.padded and self.score > 0 and not self.exclusion_reason,
            "exclusion_reason": self.exclusion_reason,
        }


@dataclass
class SearchResult:
    hits: list[Hit]
    query: str
    terms: list[str]
    expansions: list[str]
    filtered: list[dict]
    coverage: float = 0.0
    candidates: list[dict] = field(default_factory=list)
    scope: dict = field(default_factory=dict)

    @property
    def ranked(self) -> list[Hit]:
        """真正命中的片段（不含为了凑满 top_k 补上的那些）。"""
        return [hit for hit in self.hits if not hit.padded and hit.score > 0 and not hit.exclusion_reason]

    def as_trace(self) -> dict:
        return {
            "query": self.query,
            "terms": self.terms,
            "scope": self.scope,
            "candidates": self.candidates,
            "expansions": self.expansions,
            "coverage": round(self.coverage, 3),
            "hits": [
                {
                    "doc_id": hit.doc_id,
                    "chunk_id": hit.chunk_id,
                    "score": round(hit.score, 4),
                    "padded": hit.padded,
                    "exclusion_reason": hit.exclusion_reason,
                    "dropped_instructions": hit.dropped_instructions,
                }
                for hit in self.hits
            ],
            "filtered": self.filtered,
        }


class Retriever:
    def __init__(self, index: BM25Index, today: date, catalog: Optional[Catalog] = None) -> None:
        self.index = index
        self.today = today
        codes = set(index.aliases.store_code_of.values())
        codes.update(code for meta in index.docs_meta.values() for code in meta.get("stores", []))
        self.catalog = catalog or Catalog(
            stores=[{"store_id": code, "store_name": index.aliases.by_store_code(code) or code}
                    for code in sorted(codes)], aliases=index.aliases)

        self._effective_to: dict[str, Optional[str]] = {}
        for doc_id, meta in index.docs_meta.items():
            successor = meta.get("superseded_by")
            if successor and successor in index.docs_meta:
                self._effective_to[doc_id] = index.docs_meta[successor].get("effective_from")

    # -- 元数据过滤 -------------------------------------------------------------

    def _eligible(
        self, doc_id: str, as_of: date, store_id: Optional[str], historical: bool = False
    ) -> Optional[str]:
        """版本区间为 [effective_from, successor.effective_from)。

        只有无明确日期的“旧版”探索允许跨版本；归档报告本身不等于失效。
        stores_explicit 区分声明范围与正文举例。
        """
        meta = self.index.docs_meta.get(doc_id, {})
        if store_id and meta.get("stores_explicit") and store_id not in (meta.get("stores") or []):
            return "文档声明只适用于 %s，与问题里的 %s 不符" % (",".join(meta.get("stores") or []), store_id)
        if historical:
            return None
        ends = self._effective_to.get(doc_id)
        if ends and as_of.isoformat() >= ends:
            return "该版本自 %s 起已被 %s 取代" % (ends, meta.get("superseded_by"))
        starts = meta.get("effective_from")
        if starts and starts > as_of.isoformat():
            return "该版本自 %s 起才生效，晚于问题所指的 %s" % (starts, as_of.isoformat())
        if meta.get("status") == "已废止" and not ends and as_of == self.today:
            return "文档已废止，且缺少可判定历史区间的取代日期"
        return None

    def _multiplier(
        self,
        doc_id: str,
        as_of: date,
        store_id: Optional[str],
        year: Optional[int],
        window: Optional[tuple[str, str]],
        numeric: bool = False,
    ) -> float:
        meta = self.index.docs_meta.get(doc_id, {})
        factor = 1.0
        title_year = meta.get("title_year")
        if year and title_year and int(title_year) != int(year):
            factor *= YEAR_PENALTY
        starts = meta.get("effective_from")
        if starts and starts > as_of.isoformat():
            factor *= FUTURE_PENALTY
        if store_id and store_id in (meta.get("stores") or []):
            factor *= STORE_HINT_BOOST
        if window and starts and window[0] <= starts <= window[1]:
            factor *= WINDOW_BOOST
        if doc_id == self.index.aliases.source_doc:
            factor *= ALIAS_DOC_PENALTY
        if numeric and meta.get("estimates_only"):
            factor *= ESTIMATE_DOC_PENALTY
        return factor

    # -- 检索 -------------------------------------------------------------------

    def _weights(self, query: str) -> dict[str, float]:
        weights: dict[str, float] = {}
        for token in tokenize(query):
            weight = SINGLE_CHAR_WEIGHT if len(token) == 1 else 1.0
            weights[token] = weights.get(token, 0.0) + weight
        return weights

    def _concept_scores(
        self, query: str, allowed: set[int]
    ) -> tuple[dict[int, float], list[str]]:
        """别名按“同一个东西”合并：一个概念只算它最像的那一种写法，不叠加。

        不这么做的话，同时列出全部写法的别名词典自己会永远排第一。
        """
        merged: dict[int, float] = {}
        expansions: list[str] = []
        for canonical in self.index.aliases.mentions(query) + self._store_concepts(query):
            variants = self.index.aliases.variants(canonical)
            best: dict[int, float] = {}
            for variant in variants:
                weights = {token: ALIAS_WEIGHT for token in tokenize(variant)}
                if not weights:
                    continue
                for position, score in self.index.score_terms(weights, allowed).items():
                    if score > best.get(position, 0.0):
                        best[position] = score
            for position, score in best.items():
                merged[position] = merged.get(position, 0.0) + score
            expansions.extend(variants)
        return merged, expansions

    def _history_factor(self, doc_id: str, historical: Optional[bool]) -> float:
        """问旧口径时，已废止的那一版才是答案，给它加权。"""
        if not historical:
            return 1.0
        meta = self.index.docs_meta.get(doc_id, {})
        return 1.6 if meta.get("superseded_by") else 0.8

    def _store_concepts(self, query: str) -> list[str]:
        import re

        found = []
        for code in re.findall(r"(?<![a-z0-9])s\d{2}(?![a-z0-9])", normalise(query)):
            canonical = self.index.aliases.by_store_code(code)
            if canonical:
                found.append(canonical)
        return found

    def _hit(self, position: int, score: float, filtered: list[dict], padded: bool = False) -> Hit:
        chunk = self.index.chunks[position]
        return Hit(
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            score=score,
            text=chunk.text,
            source_text=chunk.source_text,
            meta=self.index.docs_meta.get(chunk.doc_id, {}),
            kind=chunk.kind,
            table_header=chunk.table_header,
            source_start=chunk.source_start,
            source_end=chunk.source_end,
            context_spans=chunk.context_spans,
            padded=padded,
            exclusion_reason=next((f["reason"] for f in filtered if f["doc_id"] == chunk.doc_id), None),
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        as_of: Optional[date] = None,
        store_id: Optional[str] = None,
        year: Optional[int] = None,
        window: Optional[tuple[str, str]] = None,
        numeric: bool = False,
        historical: Optional[bool] = None,
    ) -> SearchResult:
        query = normalise(query)
        time = parse_time(query, self.today)
        explicit_as_of = as_of is not None and as_of != self.today
        as_of = as_of or time.as_of or self.today
        year = year or time.year
        if store_id is None:
            known, unknown = self.catalog.find_store(query)
            store_id = known or unknown
        if store_id:
            store_id = normalise(store_id).strip().upper()
        if historical is None:
            historical = wants_historical(query)
        # A date always constrains versions, including questions containing 当时/以前.
        historical = bool(historical and not time.windows and not explicit_as_of)
        filtered: list[dict] = []
        excluded: set[str] = set()
        for doc_id in self.index.docs_meta:
            reason = self._eligible(doc_id, as_of, store_id, historical)
            if reason:
                excluded.add(doc_id)
                filtered.append({"doc_id": doc_id, "reason": reason})
        allowed = {i for i, chunk in enumerate(self.index.chunks) if chunk.doc_id not in excluded}
        top_k = max(1, min(top_k, len(self.index.chunks) or 1))

        scores = self.index.score_terms(self._weights(query), allowed)
        concepts, expansions = self._concept_scores(query, allowed)
        for position, score in concepts.items():
            scores[position] = scores.get(position, 0.0) + score
        best_of_doc: dict[str, float] = {}
        for position, score in scores.items():
            doc_id = self.index.chunks[position].doc_id
            best_of_doc[doc_id] = max(best_of_doc.get(doc_id, 0.0), score)
        kinds = focus_kinds(query)
        focus_boost = {
            position: SOURCE_FOCUS_BOOST if any(carries(kind, self.index.chunks[position].source_text)
                                              for kind in kinds) else 1.0
            for position in scores
        }
        adjusted: list[tuple[float, int]] = []
        for position, score in scores.items():
            doc_id = self.index.chunks[position].doc_id
            total = score + DOC_PRIOR * best_of_doc.get(doc_id, 0.0)
            adjusted.append(
                (
                    total
                    * self._multiplier(doc_id, as_of, store_id, year, window, numeric)
                    * self._history_factor(doc_id, historical)
                    * focus_boost[position],
                    position,
                ),
            )
        adjusted.sort(key=lambda item: (-item[0], item[1]))

        hits: list[Hit] = []
        taken: set[int] = set()
        per_doc: dict[str, int] = {}
        for score, position in adjusted:
            chunk = self.index.chunks[position]
            if per_doc.get(chunk.doc_id, 0) >= MAX_CHUNKS_PER_DOC:
                continue
            per_doc[chunk.doc_id] = per_doc.get(chunk.doc_id, 0) + 1
            taken.add(position)
            hit = self._hit(position, score, filtered)
            hits.append(hit)
            if len(hits) >= top_k:
                break

        # 契约 §4：索引里的片段够的时候必须恰好给 top_k 条。
        # 每篇文档只占一格的规则、以及“一个词都没命中”的片段，都可能让结果不足，
        # 这里按分数从高到低补齐；补上的标成 padded，问答链路不会拿它们作答。
        if len(hits) < top_k:
            scored = {position for _, position in adjusted}
            remaining = [(score, position) for score, position in adjusted if position not in taken]
            # 一个词都没命中的片段用来垫最后几格：每篇文档先出一段，
            # 同一篇连着占满几格没什么意义。
            unscored: dict[str, list[int]] = {}
            for position in sorted(allowed):
                if position in taken or position in scored:
                    continue
                unscored.setdefault(self.index.chunks[position].doc_id, []).append(position)
            while any(unscored.values()):
                for positions in unscored.values():
                    if positions:
                        remaining.append((0.0, positions.pop(0)))
            for score, position in remaining:
                if len(hits) >= top_k:
                    break
                taken.add(position)
                hits.append(self._hit(position, score, filtered, padded=True))
            # 契约 §4 还要求“按相关性从高到低”：补齐之后整体再排一次。
            # 每篇文档只占一格是挑片段的规则，不是排序的规则。
            hits.sort(key=lambda hit: -hit.score)
        # Only after eligible candidates are exhausted may excluded chunks fill the
        # API's count contract. Their applicability-adjusted relevance is zero;
        # ranked and the answer tool never expose these as factual evidence.
        if len(hits) < top_k:
            for position, chunk in enumerate(self.index.chunks):
                if chunk.doc_id in excluded:
                    hits.append(self._hit(position, 0.0, filtered, padded=True))
                    if len(hits) >= top_k:
                        break
        hits.sort(key=lambda hit: -hit.score)

        return SearchResult(
            hits=hits,
            query=query,
            terms=content_tokens(query),
            expansions=expansions,
            filtered=filtered,
            coverage=self._coverage(query, adjusted, top_k),
            scope={"as_of": as_of.isoformat(), "store_id": store_id,
                   "year": year, "historical": historical, "window": window},
            candidates=[{"chunk_id": self.index.chunks[position].chunk_id,
                         "doc_id": self.index.chunks[position].doc_id,
                         "score": round(score, 4),
                         "lexical_score": round(scores[position], 4),
                         "source_focus_boost": focus_boost[position],
                         "matched_terms": sorted(set(content_tokens(query)) &
                                                 set(self.index._tokens_of(self.index.chunks[position])))}
                        for score, position in adjusted],
        )

    def _coverage(self, query: str, adjusted: list[tuple[float, int]], top_k: int) -> float:
        """问题被最好的那几个片段覆盖了多少。

        只看真正命中的片段：一个词都没命中时（“zzzqqq”），覆盖率就是 0，
        这是定义，不是异常——为了凑满 top_k 补上的片段不参与这个判断。
        """
        candidates = adjusted[: max(1, top_k)]
        if not candidates:
            return 0.0
        terms = content_tokens(query)
        return max(self.index.coverage(terms, position) for _, position in candidates)


def build_retriever(kb_dir: Path, index_path: Path, today: date, rebuild: bool = False) -> Retriever:
    return Retriever(load_index(kb_dir, index_path, rebuild=rebuild), today)
