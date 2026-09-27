"""Render a clarification state; model prose is never a policy answer."""
from .llm import LLMError
from .schemas import Answer

# These are API/UI fields, not a policy vocabulary or a language rule engine.
FIELDS = {'date_range': '日期范围', 'store': '门店', 'product': '商品',
          'metric': '指标', 'question': '需要核对的问题和范围'}


def render_clarification(payload, trace):
    if set(payload) == {'answer_type', 'missing_fields'}:
        selected = payload['missing_fields']
        if (not isinstance(selected, list) or not 1 <= len(selected) <= len(FIELDS)
                or any(not isinstance(k, str) or k not in FIELDS for k in selected)
                or len(set(selected)) != len(selected)):
            raise LLMError('clarification_binding', '澄清字段必须是已声明的不重复字段')
        mode = 'typed_fields'
    elif set(payload) == {'answer_type', 'answer'}:
        text = payload['answer']
        if not isinstance(text, str) or not 0 < len(text.strip()) <= 1200:
            raise LLMError('clarification_binding', '旧澄清状态结构无效')
        # Compatibility reads only known field labels. The ENTIRE free prose,
        # including any policy assertion, is discarded and remains only in trace.
        selected = [key for key, label in FIELDS.items() if label in text
                    or key == 'date_range' and '日期' in text]
        selected = selected or ['question']
        mode = 'legacy_state'
    else:
        raise LLMError('clarification_binding', '澄清状态不能附带自由事实字段')
    labels = [label for key, label in FIELDS.items() if key in selected]
    joined = labels[0] if len(labels) == 1 else '、'.join(labels[:-1]) + '和' + labels[-1]
    trace.step('clarification_state', {'fields':selected, 'source':mode, 'policy_claims_rendered':False})
    return Answer('请补充' + joined + '。', 'clarify')
