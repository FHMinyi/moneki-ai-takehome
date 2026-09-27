# G305真实失败后的 mixed 修复（Issue26）

执行起点 **4591fab9a80ef63c440b9a117dbbc4fcbf03c430**，新树 `g3-mixed-repair`，分支 `codex/g3-03-live-mixed-repair`。旧执行树已归档，本轮未恢复/使用。产品固定点 **3d84556d1b1e522b4eadd817df2c451cb2361093**：只修改 `starter/kbqa/mixed_answer.py`，没有改G302文档协议、live.py、timeparse/planner或公共评分器。G302/G304并行修复后按主会话顺序集成。

**本轮0新增提供方请求。** 原G305在4591fab的完整真实55结果67.5/100、40/55保持原样。本票免费重放不能替代唯一授权的完整真实复验，也没有使用剩余定向名额。

## 根因与行为

| 真实失败 | 已核实的原选择 | 修复边界 |
|---|---|---|
| C07 | S04/P11的7月→8月，qty236→72；KB029原文毛利率低于35%、损耗。不是A/B倒置 | 无明确指标/精确区间、无趋势附件的文档原因请求，可使用所问粗范围内、有适用原文的补充对照；先列文档材料，再标明数据只是补充，B−A由代码计算 |
| T02首轮 | P04，6/29–7/5→7/6–7/12，qty102→0；KB021原料质检不合格/拒收、生效7/6 | 不把默认7月整月或默认net_revenue冒充用户明确约束；精确日期、明确指标、附件范围、倒序、错误主体仍拦 |
| H04 | KB025通知45 + KB001建档价口径，二者都实际检索、当前适用 | 不再要求价格和口径出自同一doc_id；每份仍核验真实身份、范围和已知明确冲突，不能用有效通用口径为不适用价格背书 |
| T03第二轮 | P06全门店6/18查询；KB023仅S02活动29；工具分组S02=29、S03/S05=42 | 通知显式标注适用S02；实际价格按真实by_store分别展示，不以任意latest_price当全门店统一价，不编造无分组的门店结果 |

原C07/T02还有后续门槛：默认指标被当显式指标，及独立事件词表不认识原因句。用户随后明确授权由同一次模型解释语义，本票删除_EVENT/支付关键词/price_policy关键词门槛，未扩原因词表、未新增模型阶段。代码仍约束真实来源、明确范围、数值、权限和容量。事件只呈现为材料记载，不自动确证因果或量化影响。

C07的“这个商品”依赖**同一个检索chunk的真实context标题**“议题四：S04吞拿鱼三明治的去留”。代码仅使用实际证据自带context，标题作为独立连续quote进入最终citations且在回答中可见；不是模型自报主体，也没有在作答后从整篇文档补取资料。

## 原记录、回放与红灯

只读来源：G305树 `docs/verification/g3-05/eval-live/{report.json,chat-trace.jsonl,model-traffic.jsonl,ledger.json}`。`source-manifest.json`记录四个完整源文件的sha256，末尾审计零变化。`original/`保存四条失败的原请求/响应/完整trace和对应11个已发生模型API记录；T03首轮成功上下文另存，仅用于重建第二轮会话。

- 首次`before-replay.txt`为4项夹具失败：index身份包含KB绝对路径，新树的evidence_id天然不同。不能把它称为产品红灯。
- 夹具修正后，除evidence_id外逐字段验证原证据与重新检索结果一致，才保留原ID用于原payload回放。`before-replay-canonical.txt`在**修改产品之前**为4项mixed_binding失败；固定测试/证据提交5e302e0。
- `first-repair.txt`、`expanded.txt`及固定`fixed-tests.txt`保留后续过程；最终25项通过。新HTTP中只按相同字段映射原ID到新检索ID，其他选择/调用不改。没有让产品接受伪造ID。
- `boundaries-first.txt`的1失败是测试把“不能逐店确认与通知一致”也当成正面“一致”声明的子串错误；修正为核对正面陈述，保留原输出，未改产品迎合测试。

## 语义边界变更的两条旧反例

`legacy-transition.txt`保留新边界下旧断言的**2FAIL/46PASS**；旧测试源逐字存于`original/legacy-test_mixed.py`、`original/legacy-test_live_replay.py`。随后仅更新这两条测试的契约预期，不修改旧日志、原题或评分器。

| 旧断言 | 新行为 | 能证明 / 不能证明 |
|---|---|---|
| 同日同店员工培训没有事件关键词，必须过滤成data | 同次模型选出的原文可作为材料记载；仍展示真实净额150 | 可证明来源、日期、数据与无因果量化；**不能证明培训确实解释异常**，这是保留的模型相关性质量反例，不记为语义安全通过 |
| 原H05网络升级背景没有支付关键词，必须剔除 | 保留模型所选三条原文（终端故障、升级背景、只收现金），27/27仍由代码计算 | 可证明三条原文真实、范围和占比；背景是否构成解释依赖模型语义，免费旧响应重放不是新的提供方理解证明 |

原明示错误门店/商品、越期事实、错误指标、倒置比较、无来源选择、金额角分、零分母等确定性反例仍按原约束检查。217通过不是“任意语义安全全绿”。

## 固定3d84556检查

| 检查 | 结果与文件 |
|---|---|
| 原4条最终选择回放 + 确定性反例/独立替换 + 本地HTTP | **25 passed**，`fixed-tests.txt`；`fixed-replay/`、`fixed-http/` |
| 原mixed/金额/会话/凭据/G302/G306受影响回归 | **217 passed**，`regression.txt`，含上述两条已明确重分类的预期 |
| 多轮/趋势实际HTTP交叉 | **14 passed**，`cross.txt`、`cross-http/` |
| 原后端独立进程 | **53 passed**，`original-final.txt`；不得与其全局替换Retriever.search夹具混跑 |
| 无Key完整公开评测 | **94/100、53/55**，`no-key/`；非真实模型评分 |
| 浏览器 | **12 passed**，四条失败问句×1280/1440/390，`browser.txt`、`browser/`；T03先重放成功首轮再发第二轮。真实HTTP、实际查询/原文/分店价格逐项核对，390截图已目视 |
| 前端构建 | `build.txt`成功，UI产品未修改 |

确定性负例包含：倒序且重新计算过的实际比较、越粗月份、明确精确日期/指标、趋势引用、错误查询主体、无支持原因、错误显式价格门店、当前问题借用已过期的单日活动。独立替换门店S01/S04及价格31.25/49.50、17.75/22.20均按各自组展示；原目标跨界测试保留。独立事件资料/DB分别改变后，销量可以下降或上升，均由B−A计算，不能用“停售原因”强迫数字下降。无分组证据不会凭latest编S02实际价。

三类证据必须分开：
1. **原payload免费回放**：C07/T02/H04/T03原选择，原11模型回合；T03上下文另有2个已保存回合。本地HTTP/浏览器无上游请求。
2. **受控新输入**：替换数据库/文档、负例和前序回归，是新构造测试输入，不是模型自行理解所得。
3. **真实模型语义未复验**：等待G302/G304等修复独立合并后由G305统一进行，当前不预测新的真实总分。

## 复现

从仓库根目录运行，必须使用新输出路径；不要覆盖已提交证据。

```bash
G303_REPAIR_OUT=/tmp/g303-repair-check/replay G303_REPAIR_HTTP=/tmp/g303-repair-check/http \
 starter/.venv/bin/python -m pytest docs/verification/g3-03-live-repair/test_replay.py \
 docs/verification/g3-03-live-repair/test_boundaries.py docs/verification/g3-03-live-repair/test_http.py -q

mkdir -p /tmp/g303-repair-check/legacy-replay
G303_REPLAY_OUT=/tmp/g303-repair-check/legacy-replay G303_HTTP_OUT=/tmp/g303-repair-check/legacy-http \
 G304_NATURAL_EVIDENCE_DIR=/tmp/g303-repair-check/legacy-replay G3_CREDENTIAL_EVIDENCE=/tmp/g303-repair-check/credentials \
 starter/.venv/bin/python -m pytest docs/verification/g3-03/test_mixed.py \
 docs/verification/g3-03/test_http.py docs/verification/g3-03/test_live_replay.py \
 docs/verification/g3-04/test_session_context.py docs/verification/g3-01/test_data_chat.py \
 docs/verification/g3-01/test_credentials.py docs/verification/g3-02/test_document_binding.py \
 docs/verification/g3-02/review-r1-r2/test_anchored_selection.py docs/verification/g3-02/review-roles/test_roles.py \
 docs/verification/g3-06/test_trend_context.py docs/verification/g3-06/test_early_plan_context.py \
 docs/verification/g3-06/test_route_regression.py -q

G303_CROSS_OUT=/tmp/g303-repair-check/cross starter/.venv/bin/python -m pytest \
 docs/verification/g3-03/integration-g304/test_cross.py -q
starter/.venv/bin/python -m pytest starter/tests -q
G303_NOKEY_OUT=/tmp/g303-repair-check/no-key starter/.venv/bin/python docs/verification/g3-03/verify_no_key.py

starter/.venv/bin/python docs/verification/g3-03-live-repair/replay_server.py /tmp/g303-repair-check/server
# 用上面打印的API端口，在frontend/执行：
BROWSER_BASE_URL=http://127.0.0.1:PORT G303_REPAIR_BROWSER=/tmp/g303-repair-check/browser \
 npx playwright test tests/g3-mixed-live-repair.spec.ts --workers=1 --output=/tmp/g303-repair-check/browser-runtime
```

`audit.json`核对5146项起点文件：只有两份按新授权更新的旧mixed测试源有差异，原版本已逐字备份；原始数据、题库、历史日志/截图/调用无变化。G305四份外部源证据hash相同；真实凭据扫描零匹配。未编辑其他执行树。

保留受控审查服务：API **http://127.0.0.1:53949**，模型53948，harness7192/API7198，var `/tmp/g303-live-mixed-repair-review/var`。它只响应保存问句的本地重放，不连接提供方。资源见`retained-resources.json`。等待主会话独立审查及具体清理指令；未合并/关Issue/归档。
