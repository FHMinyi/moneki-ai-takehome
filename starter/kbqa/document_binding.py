"""Check source-anchored question/attribute bindings from the SAME selection.

This is a conservative extraction contract, not an entailment model. No domain
synonym list is added: equivalent names must come from the actual KB aliases.
Only bounded conflicts are checked; same-response semantic interpretation is not
a deterministic entailment guarantee. Uncertainty never proves policy absence.
"""
import re
from .tokenizer import normalise, STOP_CHARS
from .entities import FOCUS_WORDS, focus_kinds
from .docfacts import carries, quantity_units, quantity_spans


def _canonical(text, aliases):
    text = normalise(text)
    for alias, canonical in sorted(aliases.canonical_of.items(), key=lambda pair: -len(pair[0])):
        text = text.replace(alias, normalise(canonical))
    return re.sub(r'[\s*`|#>]', '', text)


def check_binding(binding, question, item, facts):
    """Return checked anchors or a reason. Model booleans are not accepted."""
    if not isinstance(binding, dict) or set(binding) != {'subject', 'attribute', 'value'}:
        return None, 'binding_requires_subject_attribute_value'
    canonical = lambda text: _canonical(text, facts.index.aliases)
    checked = []
    question_spans = []
    for role in ('subject', 'attribute'):
        anchors = binding[role]
        if not isinstance(anchors, list) or not 1 <= len(anchors) <= 4:
            return None, role + '_anchors_missing'
        for anchor in anchors:
            if not isinstance(anchor, dict) or set(anchor) != {'question', 'source', 'text'}:
                return None, 'invalid_anchor_structure'
            q, ref, text = anchor['question'], anchor['source'], anchor['text']
            if not isinstance(q, str) or not q.strip() or normalise(q) not in normalise(question):
                return None, 'question_anchor_not_literal'
            if not isinstance(text, str) or not text.strip():
                return None, 'source_anchor_empty'
            if ref == 'quote':
                source = item
            elif ref == 'title' and role == 'subject' and isinstance(item['metadata'].get('title'),str):
                source = {'quote':item['metadata']['title'],'source_start':0}
            elif type(ref) is int and 0 <= ref < len(item['context']):
                source = item['context'][ref]
            else:
                return None, 'source_anchor_not_selected_context'
            position = source['quote'].find(text)
            if position < 0:
                return None, 'source_anchor_not_literal'
            same = canonical(q) == canonical(text)
            if role == 'subject':
                subject = re.sub(r'[\s\W_]', '', normalise(q))
                named = bool(facts.index.aliases.strict_mentions(q))
                if (not named and (len(subject) < 2 or subject.isdigit()
                        or all(c in STOP_CHARS for c in subject)
                        or any(q == word for _, words in FOCUS_WORDS for word in words))):
                    return None, 'subject_is_not_a_business_subject'
            if role == 'attribute' and any(q == word and carries(k, text)
                    for k, words in FOCUS_WORDS if k in {'duration','clock','money','count','value'}
                    for word in words):
                return None, 'value_shape_cannot_replace_business_attribute'
            q_entities = set(facts.index.aliases.mentions(q))
            s_entities = set(facts.index.aliases.strict_mentions(text))
            same_entity = bool(q_entities) and q_entities == s_entities
            # Existing focus shapes permit procedural/reason questions without
            # demanding that interrogative words occur in declarative evidence.
            focus_match = role == 'attribute' and any(
                q == word and carries(k, text)
                for k, words in FOCUS_WORDS if k in {'reason','rule'} for word in words)
            # Translation remains interpretation by this same model response;
            # exact spans and value shape remain checked, never a support bool.
            translation = role == 'attribute' and bool(re.search(r'[a-zA-Z]{3}', text)) and not re.search(r'[\u3400-\u9fff]', text) and bool(re.search(r'[\u3400-\u9fff]', q))
            if not (same or same_entity or focus_match or translation):
                return None, role + '_conflict'
            # When both sides explicitly qualify the same head, different
            # adjacent modifiers are a concrete conflict. An unqualified source
            # is not assumed to contradict an implicit actor (e.g. attendance).
            if role == 'subject' and same:
                def modifier(prefix):
                    cleaned = re.sub(r'[\s*`|#>]', '', normalise(prefix))
                    found = re.search(r'[\u3400-\u9fff]+$', cleaned)
                    return found.group(0) if found else ''
                q_at = normalise(question).find(normalise(q))
                left_q = modifier(normalise(question)[:q_at])
                left_source = modifier(source['quote'][:position])
                if (len(left_q) >= 2 and len(left_source) >= 2
                        and not left_q.endswith(left_source) and not left_source.endswith(left_q)):
                    return None, 'explicit_subject_modifier_conflict'
            position_q = normalise(question).find(normalise(q))
            question_spans.append((position_q, position_q + len(normalise(q)), role))
            checked.append({'role': role, 'question': q, 'quote': text,
                            'source_start': None if ref == 'title' else source['source_start'] + position,
                            'source_end': None if ref == 'title' else source['source_start'] + position + len(text),
                            'source_field': 'metadata.title' if ref == 'title' else 'visible_text',
                            'context': ref, 'interpretation': 'translation' if translation else 'value_shape' if focus_match else 'kb_alias' if same_entity and not same else 'literal'})
    value = binding['value']
    if not isinstance(value, dict) or set(value) != {'kind', 'question', 'text'}:
        return None, 'invalid_value_structure'
    kind, q, text = value['kind'], value['question'], value['text']
    kinds = {k: words for k, words in FOCUS_WORDS}
    if not isinstance(kind, str) or not isinstance(q, str) or not isinstance(text, str):
        return None, 'invalid_value_anchor'
    if kind == 'text':
        if q or text:
            return None, 'text_value_must_be_empty'
        if any(k != 'entity' for k in focus_kinds(question)):
            return None, 'requested_value_shape_omitted'
    else:
        if kind not in kinds or q not in kinds[kind] or normalise(q) not in normalise(question):
            return None, 'unknown_question_value_shape'
        if not text or text not in item['quote'] or not carries(kind, text):
            return None, 'value_not_supported_by_selected_clause'
    if kind == 'duration':
        focus_end = normalise(question).find(normalise(q)) + len(q)
        for anchor in checked:
            if anchor['role'] != 'subject' or anchor['context'] != 'quote':
                continue
            q_start = normalise(question).find(normalise(anchor['question']))
            s_start = anchor['source_start'] - item['source_start']
            follows_focus = q_start >= focus_end and not normalise(question)[focus_end:q_start].strip()
            follows_quantity = any(not item['quote'][end:s_start].strip()
                                   for _, end in quantity_spans('duration', item['quote']) if end <= s_start)
            if follows_focus and follows_quantity:
                return None, 'duration_modifier_cannot_be_subject'
    quote_anchors = [a for a in checked if a['context'] == 'quote']
    if text:
        offset = item['quote'].find(text) + item['source_start']
        quote_anchors.append({'source_start':offset, 'source_end':offset + len(text)})
    if not quote_anchors:
        return None, 'heading_only_binding'
    # A subject in one clause and an unrelated attribute/value in another do
    # not form a support relation even when the extractor returns a paragraph.
    lo, hi = min(a['source_start'] for a in quote_anchors), max(a['source_end'] for a in quote_anchors)
    between = item['quote'][lo-item['source_start']:hi-item['source_start']].rstrip('。！？!?；;')
    if re.search(r'[。！？!?；;]', between):
        return None, 'anchors_cross_clauses'
    # Protect modifiers omitted immediately between the stated subject and
    # the question's focus. This narrow check catches a dropped appeal/claim
    # qualifier without turning the whole question into a lexical coverage gate.
    lowered = normalise(question)
    focuses = [(lowered.find(normalise(w)), len(w)) for _, words in FOCUS_WORDS for w in words
               if normalise(w) in lowered]
    for start, end, role in question_spans:
        if role != 'subject':
            continue
        next_focus = min((a for a, _ in focuses if a >= end), default=end)
        gap = lowered[end:next_focus]
        for a, b, _ in question_spans:
            if a >= end and b <= next_focus:
                gap = gap.replace(lowered[a:b], ' ')
        # Only the immediate qualifier attached to the stated subject is
        # a deterministic omission check. Do not turn distant request wording,
        # temporal narration or translation into a whole-question match gate.
        stripped = gap.lstrip(''.join(STOP_CHARS) + ' ')
        first = re.match(r'[^' + re.escape(''.join(STOP_CHARS)) + r'\s，。！？?！、:：；;]+', stripped)
        qualifier = first.group(0) if first else ''
        source_subjects = [x['quote'] for x in checked if x['role']=='subject']
        same_script = any(re.search(r'[\u3400-\u9fff]', x) for x in source_subjects)
        if len(qualifier) >= 2 and same_script and re.sub(r'[\W_]', '', canonical(qualifier)) not in re.sub(r'[\W_]', '', canonical(item['quote'])):
            return None, 'omitted_subject_qualifier'
    # A quantitative question may specify its business action AFTER the
    # focus ("how long until ..."). Require its terminal content head to have
    # an attribute anchor. Reuse existing focus/claim parsing, not an action list.
    scalar_focuses = [(lowered.find(normalise(w)), len(w))
        for k, words in FOCUS_WORDS if k in {'duration','clock','money','count','value'}
        for w in words if normalise(w) in lowered]
    attribute_questions = ' '.join(a['question'] for a in checked if a['role']=='attribute')
    for pos, length in scalar_focuses:
        if any(other <= pos and other + size > pos + length for other, size in scalar_focuses):
            continue
        tail = re.split(r'[。！？!?；;]', lowered[pos+length:], maxsplit=1)[0]
        for _, words in FOCUS_WORDS:
            for word in sorted(words, key=len, reverse=True):
                tail = tail.replace(normalise(word), ' ')
        unit_only = tail.strip(''.join(STOP_CHARS) + ' ，、:：')
        terms = [] if unit_only in quantity_units(kind, text) else facts._claim_terms(tail)
        if terms and terms[-1] not in normalise(attribute_questions):
            return None, 'post_focus_business_predicate_omitted'
    return checked, None
