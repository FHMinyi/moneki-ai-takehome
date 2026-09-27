"""Typed mixed operations over executed calls and request-local document spans.

The model selects identities and roles, never operands, operators, verdicts or
causal prose. Numeric roles have a closed grammar; event text is an attributed
extract, not a claim that correlation proves the cause. This bounded checker is
not a general semantic entailment classifier.
"""
import json
import re
from datetime import date
from decimal import Decimal

from . import render as R
from .data_answer import render_data
from .llm import LLMError
from .schemas import Answer
from .timeparse import parse_time
from .tokenizer import normalise
from .tools import round2

_TARGET = re.compile(r'目标(?P<attribute>净营业额|营业额|销售额|销量|订单数)?(?:为|是|[:：])?[¥￥]?(?P<value>\d[\d,]*(?:\.\d+)?)(?P<unit>份|杯|件|单|元)')
_PRICE = re.compile(r'(?:调整为|调为|现价|活动价|售价为|售价|价格为)[¥￥]?(?P<value>\d+(?:\.\d+)?)(?:元)?')
_EVENT = re.compile(r'停业|不营业|闭店|停售|暂停|故障|网络异常|只收现金|现金结算|中断|整改|停电|施工')
_PRICE_POLICY = re.compile(r'建档价|unit_price|维表')


def compact(text):
    return re.sub(r'[\s*`|#>]', '', normalise(text))


def _source(item):
    return ' '.join([item['quote'], item['metadata'].get('title', '')] + [c['quote'] for c in item['context']])


def _fact_scope(item, params, catalog, *, product=True):
    meta = item['metadata']
    named_store, _ = catalog.find_store(item['quote'])
    named_product, _ = catalog.find_product(item['quote'])
    if named_store and params.get('store_id') and named_store != params['store_id']:
        raise ValueError('原文直接主体门店与查询不一致，标题不能覆盖正文')
    if product and named_product and params.get('product_id') and named_product != params['product_id']:
        raise ValueError('原文直接主体商品与查询不一致，标题不能覆盖正文')
    stores = meta.get('stores') or []
    if meta.get('stores_explicit') and (not params.get('store_id') or params['store_id'] not in stores):
        raise ValueError('文档门店范围不能绑定这次查询')
    if params.get('store_id') and not meta.get('stores_explicit'):
        codes = set(re.findall(r'\bS\d+\b', _source(item), re.I))
        if codes and params['store_id'] not in codes:
            raise ValueError('文档主体门店与查询不一致')
    if product and params.get('product_id'):
        pid = params['product_id']; name = catalog.product_name(pid)
        mentions = catalog.aliases.strict_mentions(_source(item))
        if compact(name) not in compact(_source(item)) and pid not in _source(item) and name not in mentions:
            raise ValueError('文档主体商品与查询不一致')


def _target_window(item):
    effective = item['metadata'].get('effective_from')
    if not effective:
        raise ValueError('目标缺少可核验的适用日期')
    window = parse_time(item['quote'], date.fromisoformat(effective)).window
    if window:
        return window
    if '当天' in item['quote']:
        return effective, effective
    raise ValueError('目标没有明确适用区间，不能套用检索日期作为目标区间')


def _event_scope(item, params):
    start, end = params['start'], params['end']
    # Source publication/effectivity and the queried sales interval are distinct.
    # Use a stated event date first; a heading can carry that date. Otherwise a
    # dated notice's effective date is the narrowest verifiable event anchor.
    windows = parse_time(item['quote'], date.fromisoformat(start)).windows
    if not windows:
        effective = item['metadata'].get('effective_from')
        windows = [(effective, effective)] if effective else []
    if not any(a <= end and b >= start for a, b in windows):
        raise ValueError('事件日期与经营查询区间不相交')
    if not params.get('store_id') and not params.get('product_id'):
        raise ValueError('异常解释需要明确的门店或商品主体')
    if not _EVENT.search(item['quote']):
        raise ValueError('所选片段没有可核对的经营事件，不能解释波动')
    return windows


def _validate_query(item, plan, mode):
    params = item['params']
    for key in ('store_id', 'product_id'):
        expected = getattr(plan, key)
        if params.get(key) != expected:
            raise ValueError('查询主体与问题不一致：' + key)
    if mode == 'price':
        if plan.window and (params.get('start'),params.get('end')) != tuple(plan.window):
            raise ValueError('价格成交查询范围与问题不一致')
        return
    window = (params.get('start_b'), params.get('end_b')) if item['tool'] == 'compare_periods' else (params.get('start'), params.get('end'))
    first_month = parse_time(plan.standalone, plan.as_of or date(2026, 9, 1)).first_month
    requested = plan.compare_window if item['tool']=='compare_periods' and plan.compare_window else plan.window
    if requested and not first_month and tuple(requested) != window:
        raise ValueError('查询日期或比较方向与问题不一致；当前区间必须是B')
    if item['tool'] == 'compare_periods':
        a = params['start_a'], params['end_a']
        if plan.compare_window and a != tuple(plan.window):
            raise ValueError('比较基期与问题不一致')
        if a[1] >= window[0]:
            raise ValueError('异常基期必须早于当前区间，不能倒置比较')
        if (date.fromisoformat(a[1])-date.fromisoformat(a[0])).days != (date.fromisoformat(window[1])-date.fromisoformat(window[0])).days:
            raise ValueError('异常区间比较必须使用等长基期')


def _limits(answer):
    from .live import _numbers_in
    if len(answer.answer)>1200 or len(set(_numbers_in(answer.answer)))>20:
        raise ValueError('组合回答超过长度或数字数量限制，请缩小范围')
    if len({c['doc_id'] for c in answer.citations})>4 or any(len(compact(c['quote']))>400 for c in answer.citations):
        raise ValueError('引用超过契约限制')
    def count(v):
        if isinstance(v,dict):return sum(count(x) for x in v.values())
        if isinstance(v,list):return sum(count(x) for x in v)
        return int(type(v) in (int,float))
    if any(len(json.dumps(e['result'],ensure_ascii=False).encode())>4096 for e in answer.data_evidence) or sum(count(e['result']) for e in answer.data_evidence)>60:
        raise ValueError('查询证据超过契约限制，请缩小范围')
    return answer


def render_mixed(payload, evidence, retrieved, plan, catalog, trace, *, search_performed=False, tool_failures=None):
    try:
        if set(payload) != {'answer_type','mode','results','facts'} or payload['answer_type']!='hybrid':
            raise ValueError('混合回答只允许mode/results/facts引用，不接受自由答案或数字')
        mode = payload['mode']
        if mode not in {'target','anomaly','payment','price'}:
            raise ValueError('未知混合操作')
        refs = payload['results']
        if not isinstance(refs,list) or len(refs)!=1 or set(refs[0])!={'call_id','metric'}:
            raise ValueError('混合操作须选一个明确的查询调用及指标')
        item = next((e for e in evidence if e['_call_id']==refs[0]['call_id']),None)
        if item is None:raise ValueError('查询调用不存在或失败')
        _validate_query(item,plan,mode)
        metric, tool, result = refs[0]['metric'], item['tool'], item['result']
        params = dict(item['params'])
        expected_tools = {'target':{'query_metrics'},'anomaly':{'query_metrics','compare_periods'},'payment':{'payment_mix'},'price':{'unit_price_check'}}
        if tool not in expected_tools[mode]:raise ValueError('工具不能用于所选混合操作')
        if mode=='anomaly' and metric!=plan.metric or mode=='price' and metric!='unit_price' or mode=='payment' and metric not in {'share_orders','share_revenue'}:
            raise ValueError('指标与混合操作或问题不一致')
        if mode=='payment' and ('金额' in plan.standalone or '营业额' in plan.standalone) and metric!='share_revenue':
            raise ValueError('金额占比不能替换为订单占比')
        if tool=='compare_periods':params.update(start=params['start_b'],end=params['end_b'])
        facts = payload['facts']
        if not isinstance(facts,list) or len(facts)>3:raise ValueError('最多选三条相关事实')
        chosen=[];citations=[];bindings=[]
        allowed_roles={'target':{'target'},'anomaly':{'reason'},'payment':{'reason'},'price':{'price','price_policy'}}[mode]
        for ref in facts:
            if not isinstance(ref,dict) or set(ref)!={'evidence_id','role'} or ref['role'] not in allowed_roles:
                raise ValueError('文档角色不符合混合操作')
            doc=retrieved.items.get(ref['evidence_id'])
            if not doc or any(d['evidence_id']==doc['evidence_id'] for _,d in chosen):raise ValueError('文档身份无效或重复')
            _fact_scope(doc,params,catalog,product=ref['role']!='price_policy')
            if ref['role']=='reason':
                source_store, _ = catalog.find_store(_source(doc))
                if params.get('store_id') and source_store != params['store_id'] and params['store_id'] not in (doc['metadata'].get('stores') or []):
                    raise ValueError('事件没有支持所问门店的主体依据')
                event_window=_event_scope(doc,params)
                if mode=='payment' and not re.search(r'现金|刷卡|扫码|支付|收款',doc['quote']):raise ValueError('事件不是支付事件')
                bindings.append(dict(role='reason',evidence_id=doc['evidence_id'],event_windows=event_window,scope=params))
            if ref['role']=='price_policy' and not _PRICE_POLICY.search(doc['quote']):raise ValueError('所选原文不说明建档价口径')
            chosen.append((ref['role'],doc));citations.append(retrieved.citation(doc))
        public={k:item[k] for k in ('tool','params','result')}
        public['call_id']=item['_call_id']
        calculations=[]
        if mode=='target':
            if len(chosen)!=1:raise ValueError('达标需要一个确定目标')
            doc=chosen[0][1]
            if retrieved.facts.index.docs_meta[doc['doc_id']].get('estimates_only'):raise ValueError('估算材料不能作为正式目标')
            targets=list(_TARGET.finditer(compact(doc['quote'])))
            if len(targets)!=1:raise ValueError('目标数值或单位不明确')
            target=targets[0];unit=target['unit'];attr=target['attribute']
            if params.get('store_id') and re.search(r'全门店|全部门店|五家门店', doc['quote']):
                raise ValueError('全门店目标不能和单店实绩比较')
            bound_metric='qty' if unit in {'份','杯','件'} else 'orders' if unit=='单' else 'net_revenue'
            if metric!=bound_metric or (attr=='销量' and bound_metric!='qty') or (attr=='订单数' and bound_metric!='orders') or (attr in {'营业额','净营业额','销售额'} and bound_metric!='net_revenue'):
                raise ValueError('目标属性、单位与实际指标不能互换')
            window=_target_window(doc)
            if parse_time(plan.standalone,plan.as_of).first_month:
                if '首月' not in doc['quote'] or window[0][:7] != doc['metadata']['effective_from'][:7]:
                    raise ValueError('首月目标必须明确且与上市通知生效月份一致')
            if window!=(params['start'],params['end']):raise ValueError('目标与实绩统计区间不同')
            actual=Decimal(str(result[metric]));goal=Decimal(target['value'].replace(',',''));gap=actual-goal
            sentence=R.describe_metrics(result,R.scope_label(window,catalog.store_name(params.get('store_id')) if params.get('store_id') else '全部门店',catalog.product_name(params.get('product_id')) if params.get('product_id') else ''),metric)
            formatter=R.money if unit=='元' else R.count
            sentence+=f'目标为 {formatter(goal)} {unit}；'+('已达标，超出' if gap>=0 else '未达标，差')+f' {formatter(abs(gap))} {unit}。'
            calculations.append(dict(operation='actual_minus_target',actual=dict(call_id=item['_call_id'],field=metric,value=float(actual)),target=dict(evidence_id=doc['evidence_id'],quote=doc['quote'],value=float(goal),unit=unit),result=float(gap),met=gap>=0))
            bindings.append(dict(role='target',evidence_id=doc['evidence_id'],metric=bound_metric,window=window,scope=params))
        elif mode=='anomaly':
            pure=render_data(json.dumps(dict(answer_type='data',results=refs)),evidence,catalog)
            sentence=pure.answer
            if tool=='compare_periods':
                calculations.append(dict(operation='period_b_minus_period_a',metric=metric,call_id=item['_call_id'],a=result['period_a'][metric],b=result['period_b'][metric],result=result['delta'][metric]))
        elif mode=='payment':
            available=result['payments']; focus=[p for p in available if p in plan.standalone]
            if not focus and any(p in plan.standalone for p in ('现金','微信','支付宝','刷卡','会员储值')):
                # Missing requested category is a real zero, not every other category.
                focus=[p for p in ('现金','微信','支付宝','刷卡','会员储值') if p in plan.standalone]
            if not focus:focus=list(available)
            lines=[]
            field='orders' if metric=='share_orders' else 'net_revenue';denom='total_orders' if field=='orders' else 'total_net_revenue'
            unit='单' if field=='orders' else '元';label='订单数' if field=='orders' else '净营业额'
            for payment in focus:
                numerator=available.get(payment,{}).get(field,0);total=result[denom]
                pct=round2(Decimal(str(numerator))*100/Decimal(str(total))) if total else None
                lines.append(f'{payment}按{label}占比 '+(f'{pct:.2f}%' if pct is not None else '无法计算（分母为零）')+f'（{R.count(numerator)} / {R.count(total)} {unit}）')
                calculations.append(dict(operation='share_percent',call_id=item['_call_id'],numerator_field=f'payments.{payment}.{field}',denominator_field=denom,numerator=numerator,denominator=total,result=pct))
            sentence=f"{params['start']} 至 {params['end']} {catalog.store_name(params.get('store_id')) if params.get('store_id') else '全部门店'}："+'；'.join(lines)+'。'
        else:
            prices=[d for role,d in chosen if role=='price']
            if len(prices)!=1:raise ValueError('现行价格须选择一个适用价格原文')
            doc=prices[0];matches=list(_PRICE.finditer(compact(doc['quote'])))
            if any(d['doc_id']!=doc['doc_id'] for role,d in chosen if role=='price_policy'):
                raise ValueError('建档价说明必须属于同一适用价格文档')
            if len(matches)!=1 or retrieved.facts.index.docs_meta[doc['doc_id']].get('estimates_only'):raise ValueError('售价不明确或只是估算')
            current=Decimal(matches[0]['value']);latest=result['latest_price'];table=result['table_unit_price']
            sentence=f"{catalog.product_name(params['product_id'])} 适用通知售价为 {current:.2f} 元。"
            if latest is None:sentence+='查询区间没有成交记录，无法核对实收单价。'
            else:sentence+=f"数据库最近成交日 {result['latest_date']} 的一笔实收单价为 {latest:.2f} 元，与通知"+('一致。' if Decimal(str(latest))==current else '不一致；实绩仍以数据库为准，原因需进一步核对。')
            if table is not None:
                delta=current-Decimal(str(table));sentence+=f'维表建档价为 {table:.2f} 元，通知价减建档价为 {delta:.2f} 元；建档价不能代替实际成交查询。'
                calculations.append(dict(operation='notice_minus_table_price',notice=dict(evidence_id=doc['evidence_id'],value=float(current)),table=dict(call_id=item['_call_id'],field='table_unit_price',value=table),result=float(delta)))
        if chosen:
            sentence+='\n'+ '\n'.join(('同期材料记载' if role=='reason' else '原文依据')+f" {d['doc_id']}："+retrieved.facts.render(d['doc_id'],d['quote']) for role,d in chosen)
            if mode in {'anomaly','payment'}:sentence+='\n以上是材料记载；未据此估算事件对经营数字的因果影响。'
        elif mode in {'anomaly','payment'}:
            if not search_performed or any(f['tool']=='search_kb' for f in tool_failures or []):raise ValueError('未成功检索，不能将工具失败当作原因未知')
            sentence+='知识库中本次未找到可核对的对应原因材料，原因无法确定。'
        public['calculations']=calculations
        answer=_limits(Answer(sentence,'hybrid' if citations else 'data',citations=citations,data_evidence=[public]))
        trace.step('mixed_binding',dict(mode=mode,source_call=item['_call_id'],bindings=bindings,calculations=calculations,selected=[d['evidence_id'] for _,d in chosen]))
        return answer
    except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError) as exc:
        raise LLMError('mixed_binding','混合回答未通过来源、指标与关系核验：%s'%exc) from exc
