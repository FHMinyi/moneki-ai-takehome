# PR37 最终集成回执

按主会话明确指令，保存6fefa99后正常合入main **03a94edb7f67fb7ce9fd5ba1771b9f0126e27c22**（G302最小doc/8192及G304日期修复）。双亲merge **d9612c8d32aae9a8805065b953ceb03578d4fbe9**，无冲突、无rebase。最终产品 **8fd8070d6118f5aa25d596ae9e37285ee63cc48c**；后续仅测试/证据/说明。无已知硬阻塞，主会话待按固定头独立验收。0新增提供方调用，真实语义统一留G305。

## 两项小修与红灯

1. **query_stores标签**：实际SQLite单店S02同日30.00/34.50两种实收价，d9612c8的正文与计算正确但trace写all。`trace-scope-red.txt`一红；**5a614ad**只按params.store_id或all记标签，`trace-scope-green.txt`一绿，正文/计算不变。
2. **单日与自然追问交叉**：`cross.txt`和`cross-http/`保存5a614ad上原14项的**2FAIL/12PASS**，提交74be0cd。成功H02后“那6月19日销量呢”，模型正确依据历史查询S02/P06，但新日期guard把未解析None当明确全量。busy用例的后续追问同因失败，busy自身正确。

**8fd8070**只改Service最小bound_entities集合：精确单日始终锁定；已解析/本轮明确实体约束；明确全部门店/所有商品绑定None并清旧改写；未知维度不写成all。趋势附件没有该mask，继续严格绑定两维，None仍是附件明确全量。未改timeparse。新增8实际HTTP正反覆盖合法历史实体但拒错日、明确S01/P05且拒旧对象、明确全量不继承旧实体、趋势无商品不许擅加P06。记录在`final-day-http/`；原14项恢复通过，含busy不修改执行中历史。

## 已完成验证及精确固定点

| 固定点 | 检查 | 结果/证据 |
|---|---|---|
| 8fd8070 | 原4失败回放/确定性反例/替换输入/实际HTTP/trace/新协议/单日交叉 | **40 passed**，`final-40.txt` |
| 8fd8070 | mixed/data/session/credentials/trend/明确日期 | **143 passed**，`final-regression.txt`；未把旧doc词语语义gate重新作门禁 |
| 8fd8070 | 原多轮/趋势HTTP交叉 | **14 passed**，`final-cross.txt`、`final-cross-http/` |
| 8fd8070 | 原后端独立进程 | **53 passed**，`final-original.txt` |
| 5a614ad | 新doc来源/结构/范围及8192上限 | **49 passed**，`doc-minimal.txt` |
| 8fd8070 | 上述最小doc实际HTTP受影响路径 | **10 passed**，`final-doc-http.txt`，每次请求8192 |
| 8fd8070 | 四条原选择浏览器390回放 | **4 passed**，`final-browser-replay.txt`；非新提供方理解 |
| 8fd8070 | mixed→最小doc→明确单日、mixed→自然单日追问，1280/390 | **4 passed**，`final-browser-protocol.txt`；trace未绑定实体字段确实缺省，实际S02/P06重新查数；390截图已目视 |
| 8fd8070 | 无Key未改公开55题 | **94/100、53/55**，`final-no-key/`，不是新真实评分 |

`protocol-date.txt`初次4项通过但三个参数化案例输出名重复，仅最后一组留存；修正SID后重新运行，全部请求独立保存于`http-protocol-date-final/`及`final-protocol-http/`。初次浏览器脚本路径错误的无测试输出也保留，不称产品失败。最终结果以上表为准。

## 快速复现

使用新路径，不覆盖历史证据。旧保存响应重放所需目录先mkdir。

```bash
mkdir -p /tmp/g303-final-review/replay
G303_REPAIR_OUT=/tmp/g303-final-review/replay G303_REPAIR_HTTP=/tmp/g303-final-review/replay-http \
 G303_INTEGRATED_HTTP=/tmp/g303-final-review/protocol G303_DAY_FOLLOWUP_OUT=/tmp/g303-final-review/day \
 starter/.venv/bin/python -m pytest docs/verification/g3-03-live-repair/test_replay.py \
 docs/verification/g3-03-live-repair/test_boundaries.py docs/verification/g3-03-live-repair/test_http.py \
 docs/verification/g3-03-live-repair/test_trace_scope.py docs/verification/g3-03-live-repair/test_integrated.py \
 docs/verification/g3-03-live-repair/test_day_followup.py -q
# 40 passed
G303_CROSS_OUT=/tmp/g303-final-review/cross starter/.venv/bin/python -m pytest \
 docs/verification/g3-03/integration-g304/test_cross.py -q
starter/.venv/bin/python -m pytest starter/tests -q
G302_HTTP_OUT=/tmp/g303-final-review/doc starter/.venv/bin/python -m pytest \
 docs/verification/g3-02-live-repair/test_selection_boundary.py -q -k minimal_protocol_real_http
```

## 保全、边界与资源

`audit-final.json`：初始5146项只有此前已授权的2旧mixed测试源变化，旧源快照逐字匹配；incoming main114项输入/新修复证据和集成前143项本票原始证据零变化；外部G305四源hash未变；真实Key扫描零匹配。旧2FAIL/46PASS语义断言记录仍在，未说成原断言全部满足。原payload回放、受控新选择和未真实复验三类界限不变。没有使用剩余付费名额。

最终审查服务（均本地免费，无提供方连接）：
- 原记录回放：API58844/model58843，harness21195/API21201，`/tmp/g303-live-mixed-repair-final/var`。
- 最小doc/日期/自然追问受控：API58836/model58835，harness21185/API21193，`/tmp/g303-mixed-doc-date-final/var`。

其余旧阶段服务仍保留，五组完整清单见`resources-final.json`。未清理或归档，等待主会话具体指令。提交截止收口阶段不再扩矩阵；没有未完成的本票必要验证。
