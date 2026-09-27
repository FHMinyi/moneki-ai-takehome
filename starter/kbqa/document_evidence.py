"""Request-scoped, extractive document evidence. No post-answer full-document lookup.

Retrieval owns applicability; this boundary owns source identity and continuous
spans. Models may select facts, never attach new prose/numbers to those facts.
The bounded claim check is not a general semantic entailment classifier.
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

    def render(self, content, question, trace):
        try:
            payload=json.loads(content)
        except (ValueError,TypeError):
            raise LLMError('document_binding','文档回答必须显式选择检索证据，不能提交自由陈述')
        if not isinstance(payload,dict) or set(payload)!={'answer_type','facts'} or payload['answer_type']!='doc':
            raise LLMError('document_binding','文档回答结构无效')
        refs=payload['facts']
        if not isinstance(refs,list) or not 1<=len(refs)<=4:
            raise LLMError('document_binding','必须选择一至四条文档事实')
        selected=[]
        for ref in refs:
            if not isinstance(ref,dict) or set(ref)!={'evidence_id'} or not isinstance(ref['evidence_id'],str):
                raise LLMError('document_binding','文档事实只接受证据ID，不接受改写的事实或数字')
            item=self.items.get(ref['evidence_id'])
            if item is None:
                raise LLMError('document_binding','证据不属于本次实际检索集合')
            if item in selected:
                raise LLMError('document_binding','文档事实重复')
            selected.append(item)
        claim=self.facts.requested_claim(question)
        citations=[]; lines=[]
        for item in selected:
            unit=self.units[item['evidence_id']]
            # Check closed subject/predicate questions against this exact span,
            # and open questions against entity and requested value shape. This
            # reuses bounded evidence checks, never invokes the mock answerer.
            ranked=self.facts.rank(question,item['doc_id'],limit=1,require_value=False,units=[unit])
            entities=set(self.facts.index.aliases.strict_mentions(question))
            source_entities=set(self.facts.index.aliases.strict_mentions(unit.text+' '+ ' '.join(c['quote'] for c in item['context'])))
            requested = re.search(r"(?:多少|几)\s*(工作日|小时|分钟|天|克|公斤|毫升|升|元|条|次|人|杯|份)", question)
            missing_measure = requested and not re.search(r"\d[\d,.]*\s*" + requested.group(1), unit.text)
            if missing_measure or not ranked or not self.facts.supports_claim(claim,unit) or not entities<=source_entities:
                trace.step('document_binding_rejected',{'evidence_id':item['evidence_id'],'required_claim':claim,'reason':'subject_or_attribute_not_supported'})
                raise LLMError('document_binding','所选证据不支持问题的主体或属性')
            citations.append(self.citation(item))
            if unit.kind=='table':
                for span in item['context']:
                    if span['quote'].strip().startswith('|') and all(h in span['quote'] for h in unit.header):
                        citations.append({'doc_id':item['doc_id'],**span,'chunk_id':item['chunk_id'],'metadata':item['metadata'],'scope':item['scope']})
            title=item['metadata'].get('title')
            label=item['doc_id']+(f'《{title}》' if title else '')
            # Table labels come from actual header cells. Every displayed fact
            # otherwise is an extract, so model prose cannot change its meaning.
            lines.append(label+'：'+self.facts.render(item['doc_id'],item['quote']))
        text='\n'.join(lines)
        from .live import _numbers_in
        if len(text)>1200 or len(set(_numbers_in(text)))>20 or len({c['doc_id'] for c in citations})>4:
            raise LLMError('document_binding','所选证据超过回答长度或数量限制')
        trace.step('document_binding',{'selected':selected,'required_claim':claim,'mode':'extractive'})
        return Answer(text,'doc',citations=citations)
