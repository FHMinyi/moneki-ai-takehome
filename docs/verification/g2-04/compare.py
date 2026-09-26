"""Compare every public question and turn, not only total scores."""
import json
from pathlib import Path
import sys
before,after,out=map(Path,sys.argv[1:])
a=json.loads(before.read_text());b=json.loads(after.read_text())
rows=[];regressions=[];turn_regressions=[]
for x,y in zip(a['questions'],b['questions']):
    assert x['id']==y['id']
    state='保持通过' if x['passed'] and y['passed'] else '新增通过' if y['passed'] else '回归' if x['passed'] else '仍未全绿'
    turns=[]
    for i,(u,v) in enumerate(zip(x['turns'],y['turns']),1):
        old_checks={c['name']:c['passed'] for c in u['checks']}
        lost=[c['name'] for c in v['checks'] if old_checks.get(c['name']) and not c['passed']]
        # New checks may become applicable after changing response type. Preserve
        # these separately from regressions in a formerly passing whole turn.
        if u['passed'] and not v['passed']:turn_regressions.append(f"{y['id']}:{i}")
        turns.append(dict(turn=i,question=v['question'],before=u['passed'],after=v['passed'],lost_checks=lost,
                          failed_after=[c['name'] for c in v['checks'] if not c['passed']]))
    if x['passed'] and not y['passed'] or y['earned']<x['earned']:regressions.append(y['id'])
    rows.append(dict(id=y['id'],category=y['category'],before=x['earned'],after=y['earned'],state=state,turns=turns))
result=dict(before_report=str(before),after_report=str(after),regressed_questions=regressions,
            regressed_passed_turns=turn_regressions,questions=rows)
out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
lines=['# 与G2-03逐题、逐轮对照','',f'问题回归：{regressions}；原通过轮次回归：{turn_regressions}。',
       '','| 题 | 前分 | 后分 | 状态 | 各轮（前→后） |','|---|---|---|---|---|']
for row in rows:
    ts='；'.join(f"{t['turn']}：{t['before']}→{t['after']}" for t in row['turns'])
    lines.append(f"| {row['id']} | {row['before']} | {row['after']} | {row['state']} | {ts} |")
lines+=['','仍未全绿的每轮失败检查、已通过检查的变化保留在同名JSON；不把部分首轮通过记作多轮整题通过。']
out.with_suffix('.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(regressed_questions=regressions,regressed_passed_turns=turn_regressions,
                     states={s:sum(r['state']==s for r in rows) for s in {r['state'] for r in rows}}),ensure_ascii=False))
