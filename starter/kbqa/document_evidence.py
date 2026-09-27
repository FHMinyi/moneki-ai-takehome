"""Request-scoped, extractive document evidence. No post-answer full-document lookup.

Retrieval owns applicability; this boundary owns source identity and continuous
spans. Models may select facts, never attach new prose/numbers to those facts.
Semantic selection belongs to the same model response, not lexical heuristics.
"""
from __future__ import annotations

import hashlib
import json
import re
from .llm import LLMError
from .schemas import Answer
from .sanitize import is_instruction_like


def insufficient_evidence(trace, source="model_state"):
    """A lack-of-support state, never a model-authored policy conclusion."""
    trace.step("insufficient_evidence", {"source": source, "policy_claims_rendered": False})
    return Answer("本次没有足够可核对的依据回答这个问题，无法确定。请补充相关资料或明确需要核对的范围。",
                  "refusal")


class DocumentEvidence:
    def __init__(self, facts, result=None, hits=None):
        self.facts = facts
        self.result = result
        self.items = {}
        self.units = {}
        self.rejected = []
        if result is None:
            return
        for hit in result.ranked if hits is None else hits:
            source = facts.index.texts[hit.doc_id]
            lo = len(re.sub(r'\s+', '', source[:hit.source_start]))
            hi = len(re.sub(r'\s+', '', source[:hit.source_end]))
            units = [u for u in facts.units(hit.doc_id) if lo <= u.start < u.end <= hi]
            for unit in units:
                # Include contiguous sentence leads, while retaining the genuine
                # hit boundary. These are candidates, not new document retrieval.
                expanded = facts._with_lead(units, unit)
                for candidate in (unit, expanded):
                    if candidate.kind == 'heading' or candidate.text.rstrip().endswith(('?', '？')):
                        continue
                    if is_instruction_like(candidate.text):
                        self.rejected.append({'doc_id':hit.doc_id,'reason':'document_instruction','text':candidate.text})
                        continue
                    cite = facts.cite(hit.doc_id, candidate.text)
                    if not cite or not lo <= candidate.start < candidate.end <= hi:
                        continue
                    _, offsets = facts.stripped(hit.doc_id)
                    start, end = offsets[candidate.start], offsets[candidate.end-1]+1
                    identity = f'{facts.index.key}:{hit.chunk_id}:{start}:{end}:' + json.dumps(result.scope, sort_keys=True)
                    eid = 'doc-' + hashlib.sha256(identity.encode()).hexdigest()[:20]
                    context = []
                    for span in hit.context_spans:
                        text = source[span['start']:span['end']]
                        if facts.cite(hit.doc_id,text) and not is_instruction_like(text):
                            context.append(dict(quote=text,source_start=span['start'],source_end=span['end']))
                    item = dict(evidence_id=eid, doc_id=hit.doc_id, chunk_id=hit.chunk_id,
                                quote=source[start:end],source_start=start,source_end=end,
                                kind=candidate.kind, context=context, score=hit.score,
                                scope=dict(result.scope),
                                metadata={k:hit.meta[k] for k in ('title','effective_from','status','stores','stores_explicit','superseded_by') if k in hit.meta})
                    self.items[eid] = item
                    self.units[eid] = candidate

    def add(self, items):
        # Only called with executor-created evidence; model input cannot add IDs.
        from .units import Unit
        added = []
        for item in items:
            if item['evidence_id'] in self.items:
                continue
            added.append(item)
            self.items[item['evidence_id']] = item
            source = self.facts.index.texts[item['doc_id']]
            lo = len(re.sub(r'\s+', '', source[:item['source_start']]))
            hi = len(re.sub(r'\s+', '', source[:item['source_end']]))
            originals = self.facts.units(item['doc_id'])
            context = set().union(*(u.context for u in originals if lo <= u.start < u.end <= hi))
            header = self.facts.table_header_for(item['doc_id'],item['quote'])
            self.units[item['evidence_id']] = Unit(item['quote'], context, item['kind'], header,
                                                 item['doc_id'], -1, lo, hi)
        return added

    def public(self):
        return list(self.items.values())

    def find(self, doc_id, unit):
        return next((e for eid,e in self.items.items() if e['doc_id']==doc_id and
                     self.units[eid].start==unit.start and self.units[eid].end==unit.end),None)

    def citation(self, item):
        return {k:item[k] for k in ('doc_id','quote','evidence_id','chunk_id','source_start','source_end','scope','metadata')}

    def _verify_source(self, item, plan=None):
        """Verify executor evidence integrity; do not infer semantic entailment."""
        source = self.facts.index.texts.get(item['doc_id'])
        if source is None:
            raise LLMError('document_binding', '证据来源不存在')
        for span in [item, *item['context']]:
            start, end = span['source_start'], span['source_end']
            if (type(start) is not int or type(end) is not int or
                    not 0 <= start < end <= len(source) or source[start:end] != span['quote']):
                raise LLMError('document_binding', '证据原文与来源位置不一致')
        chunk = next((c for c in self.facts.index.chunks if c.chunk_id == item['chunk_id']
                      and c.doc_id == item['doc_id']), None)
        if chunk is None or not chunk.source_start <= item['source_start'] < item['source_end'] <= chunk.source_end:
            raise LLMError('document_binding', '证据不属于所检索原文块')
        context_offsets = {(c['start'], c['end']) for c in chunk.context_spans}
        if any((c['source_start'], c['source_end']) not in context_offsets for c in item['context']):
            raise LLMError('document_binding', '证据上下文不属于所检索原文块')
        actual = self.facts.index.docs_meta[item['doc_id']]
        if any(actual.get(k) != v for k,v in item['metadata'].items()):
            raise LLMError('document_binding', '证据元数据与来源不一致')
        if plan is not None:
            meta = item['metadata']
            if (plan.store_id and meta.get('stores_explicit') and
                    plan.store_id not in meta.get('stores', [])):
                raise LLMError('document_binding', '证据明确适用门店与问题不一致')
            if plan.as_of and meta.get('effective_from') and meta['effective_from'] > plan.as_of.isoformat():
                raise LLMError('document_binding', '证据尚未生效')
        if len(re.sub(r'\s+', '', item['quote'])) > 400:
            raise LLMError('document_binding', '引用原文超过容量限制')

    def render(self, content, question, trace, *, plan=None):
        try:
            payload=json.loads(content)
        except (ValueError,TypeError):
            raise LLMError('document_binding','文档回答必须显式选择检索证据，不能提交自由陈述')
        if not isinstance(payload,dict) or set(payload)!={'answer_type','facts'} or payload['answer_type']!='doc':
            raise LLMError('document_binding','文档回答结构无效')
        refs=payload['facts']
        if not isinstance(refs,list) or not 1<=len(refs)<=4:
            raise LLMError('document_binding','必须选择一至四条文档事实')
        selected=[]; legacy=0
        for ref in refs:
            # Compatibility with saved/older responses: legacy binding is never
            # interpreted, rendered, or treated as proof of semantic support.
            if (not isinstance(ref,dict) or set(ref) not in ({'evidence_id'}, {'evidence_id','binding'})
                    or not isinstance(ref['evidence_id'],str)
                    or ('binding' in ref and not isinstance(ref['binding'],dict))):
                raise LLMError('document_binding','文档事实只能选择实际证据ID，不接受自由陈述')
            item=self.items.get(ref['evidence_id'])
            if item is None:
                raise LLMError('document_binding','证据不属于本次实际检索集合')
            if any(p['evidence_id'] == item['evidence_id'] for p in selected):
                raise LLMError('document_binding','文档事实重复')
            self._verify_source(item, plan)
            legacy += int('binding' in ref)
            selected.append(item)
        citations=[]; lines=[]
        for item in selected:
            unit=self.units[item['evidence_id']]
            citations.append(self.citation(item))
            # Include the actual context that the selecting model saw, notably
            # table headers. All offsets above were checked against the source.
            for span in item['context']:
                cite={'doc_id':item['doc_id'],**span,'chunk_id':item['chunk_id'],
                      'metadata':item['metadata'],'scope':item['scope']}
                if cite not in citations:
                    citations.append(cite)
            if unit.kind=='table' and not any(
                    c['quote'].strip().startswith('|') and all(h in c['quote'] for h in unit.header)
                    for c in item['context']):
                raise LLMError('document_binding','表格证据缺少实际检索表头')
            title=item['metadata'].get('title')
            label=item['doc_id']+(f'《{title}》' if title else '')
            lines.append(label+'：'+self.facts.render(item['doc_id'],item['quote']))
        text='\n'.join(lines)
        from .live import _numbers_in
        if len(text)>1200 or len(set(_numbers_in(text)))>20 or len({c['doc_id'] for c in citations})>4:
            raise LLMError('document_binding','所选证据超过回答长度或数量限制')
        trace.step('document_binding',{'selected':selected,'mode':'extractive',
                    'semantic_selection':'same_model','legacy_bindings_ignored':legacy,
                    'verified':['retrieved_identity','source_offsets','metadata','explicit_scope','capacity']})
        return Answer(text,'doc',citations=citations)
