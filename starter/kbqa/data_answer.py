"""Render data from typed tool references; model-authored numbers are never used."""
import json
import re

from . import render as R
from .llm import LLMError
from .schemas import Answer


def render_data(content: str, evidence: list[dict], catalog) -> Answer:
    try:
        payload = json.loads(content)
        if set(payload) != {'answer_type', 'results'} or payload['answer_type'] != 'data':
            raise ValueError('数据回答必须使用 data 结果引用')
        selected = payload['results']
        if not isinstance(selected, list) or not 1 <= len(selected) <= 3:
            raise ValueError('一次选取 1 至 3 个结果')
        calls = {e['_call_id']: e for e in evidence}
        sentences, used = [], []
        for selection in selected:
            if not isinstance(selection, dict) or set(selection) != {'call_id', 'metric'}:
                raise ValueError('只允许 call_id 与 metric，数值由代码生成')
            metric = selection['metric']
            if metric not in R.METRIC_LABELS:
                raise ValueError('未知指标')
            item = calls.get(selection['call_id'])
            if item is None:
                raise ValueError('引用的调用不存在或未成功')
            params, result, tool = item['params'], item['result'], item['tool']
            def scope(value):
                store = catalog.store_name(value['store_id']) + ' ' + value['store_id'] if value.get('store_id') else ''
                product = catalog.product_name(value['product_id']) + ' ' + value['product_id'] if value.get('product_id') else ''
                return R.scope_label((value['start'], value['end']), store, product)
            if tool == 'query_metrics':
                sentence = '%s：%s %s。' % (scope(result), R.METRIC_LABELS[metric], R.metric_value(metric, result))
                if metric == 'aov' and result['aov'] is None:
                    sentence = '%s：没有有效订单，客单价无法计算。' % scope(result)
            elif tool == 'compare_periods':
                sentence = R.describe_compare(result, metric, scope(result['period_a']), scope(result['period_b']))
            elif tool == 'payment_mix':
                sentence = R.describe_payment(result, scope(params))
            elif tool == 'top_products':
                sentence = R.describe_top(result, scope(params), limit=params.get('limit', 3))
            elif tool == 'by_store':
                sentence = R.describe_by_store(result, scope(params))
            elif tool == 'by_store_category':
                sentence = R.describe_category(result, scope(params))
            elif tool == 'daily_metrics' and metric == 'net_revenue':
                sentence = R.describe_daily(result, scope(params))
            else:
                raise ValueError('这个工具结果暂不支持该数据回答，请改用区间指标查询')
            sentences.append(sentence)
            public = {k: item[k] for k in ('tool', 'params', 'result')}
            if public not in used:
                used.append(public)
        text = '\n'.join(sentences)
        if len(text) > 1200 or len(set(re.findall(r'\d+(?:\.\d+)?', text))) > 20:
            raise ValueError('回答超过契约容量，请缩小查询范围')
        if any(len(json.dumps(e['result'], ensure_ascii=False).encode()) > 4096 for e in used):
            raise ValueError('证据超过契约容量，请缩小查询范围')
        def count_numbers(value):
            if isinstance(value, dict):
                return sum(count_numbers(v) for v in value.values())
            if isinstance(value, list):
                return sum(count_numbers(v) for v in value)
            return int(type(value) in (int, float))
        if sum(count_numbers(e['result']) for e in used) > 60:
            raise ValueError('证据数字过多，请缩小查询范围')
        return Answer(text, 'data', data_evidence=used)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise LLMError('data_binding', '数据回答未通过字段与查询绑定：%s' % exc) from exc
