# G3-06 每日趋势显式引用验收

固定起点 `587ae820185cd10839e189efa9fb2ed8863d1ca5`，独立工作树 `/Users/minyi/.codex/worktrees/g3-06-trend-context/moneki-ai-takehome`。所有源码、构建、测试均在该树执行。`protected-before.json` 使用 `git ls-files -z` 逐一记录 3186 个已有数据、评分器和历史证据文件；`preservation.json` 重新计算后为 0 差异。共享根旧未跟踪草稿没有复制或恢复。

## 修改前与最终验证

| 阶段 | 命令 | 结果 |
| --- | --- | --- |
| 修改前，`587ae82` | `env -u LLM_API_KEY -u LLM_BASE_URL -u LLM_MODEL starter/.venv/bin/python -m pytest starter/tests/test_daily_trend.py docs/verification/g3-01/test_data_chat.py -q` | 21 passed。首次因独立树尚无 `.venv` 而无法启动；隔离安装依赖后补跑。不是第三关完整基线。 |
| 完成后 | `env -u LLM_API_KEY -u LLM_BASE_URL -u LLM_MODEL starter/.venv/bin/python -m pytest docs/verification/g3-06/test_trend_context.py docs/verification/g3-01/test_data_chat.py starter/tests -q` | 84 passed，1 条第三方 TestClient 弃用警告。 |
| 完成后 | `npm --prefix frontend run build` | TypeScript/Vite 成功；Vite/AntD 既有 bundle 警告。 |
| 完成后 | `DAILY_EVIDENCE_DIR=../docs/verification/g3-06/regression-daily BROWSER_BASE_URL=http://127.0.0.1:8036 npm run test:browser -- tests/daily-trend.spec.ts tests/g3-trend-context.spec.ts`（在 `frontend/`） | 11 passed，含 G1 趋势 4 项和 G3-06 7 项。首次浏览器脚本在 Drawer 关闭动画时点选门店失败；补显式隐藏等待后通过，记录为脚本时序修正。 |
| 完成后 | `starter/.venv/bin/python docs/verification/g3-06/replay_controlled.py` | 2/2 受控模型 HTTP 样本；本地受控模型仅给工具调用，结果来自实际清洗数据库。输出 `controlled-http.json` 保存原请求、回答、完整 trace、独立 metrics API 期望。 |
| 完成后 | `G306_MODEL_URL=http://127.0.0.1:9036 G306_EVIDENCE_DIR=../docs/verification/g3-06/browser-controlled BROWSER_BASE_URL=http://127.0.0.1:8037 npm run test:browser -- tests/g3-trend-context.spec.ts --workers=1`（在 `frontend/`） | 7 passed。受控模型只产生工具调用与最终选择；真实工具/数据库结果通过浏览器侧独立 metrics API 核对。 |
| 真实调用前离线守卫 | `starter/.venv/bin/python -m pytest docs/verification/g3-06/test_live_budget.py -q` | 7 passed；覆盖出站前预留、完整 usage 释放、无/不完整 usage 保留、余额不足禁止出站和每 chat 尝试数上限。 |
| 已授权真实样本，`64c3291` | `starter/.venv/bin/python docs/verification/g3-06/run_live_samples.py` | 2 次 chat，各 2 次模型出站，共 4 次；均为 `data`，没有 trace 错误。样本、完整 trace 与独立账本见 `live/`。 |
| 独立 SQL 复核 | `starter/.venv/bin/python docs/verification/g3-06/audit_live.py` | 2/2；只读 SQLite 分别计算净额、退款、去重订单、销量与客单价，逐项等于实际业务工具结果，并核对原问题、引用、有效条件及来源、工具参数、回答数字。 |

浏览器服务使用独立 `VAR_DIR=/tmp/moneki-g306-browser-var`、端口 8036、无 Key；受控服务使用独立 `/tmp/moneki-g306-live-var`、端口 8037 与本地模型端口 9036。截图与逐宽度 HTTP/trace 在 `browser/`、`browser-controlled/`，第一关趋势回归截图在 `regression-daily/`。测试输出不覆盖历史证据。

## 八项验收映射

1. `DailyTrend` 只在有效响应的首尾日期与当前生效筛选一致时显示“加入提问”；引用整块日期、门店和固定净营业额指标。浏览器在选中中间日期后验证引用仍为完整范围，并覆盖加载错误状态。
2. `ChatSidebar` 的待发引用最多一张；删除、替换、筛选草稿变化、已发消息固定范围、重试携原引用、新会话清空与迟到请求丢弃由 `g3-trend-context.spec.ts` 验证。
3. `context` 可选且仅接受 `daily_trend` 的五个字段。`test_trend_context.py` 覆盖额外 SQL/工具/金额字段、无效日期/门店/类型的 HTTP 200 结构化拒答和旧两字段请求。
4. `context_resolution` trace 记录有效条件、每字段来源与覆盖；单轮“这段时间”使用引用，明确七月 S01 使用文字新条件，“这一周”要求澄清。HTTP 与受控样本均检查。
5. 受控 HTTP 的 `data_evidence` 等于独立 metrics API 同条件结果；测试复制原始 SQLite、修改一条有效销售金额、重建到另一个独立 `VAR_DIR`，同一引用的净营业额随之增加 1000 元。
6. `request`、`context_validation`、`context_resolution`、`plan`、`tool` 与模型请求/输出保存在 trace。`replay_controlled.py` 保存可重放原请求，且同条件结果与实际工具一致。
7. 1280、1440、390 的真实 Chromium/后端/数据库证据见 `browser/lifecycle-*.json` 与截图；同一路径还在 `browser-controlled/` 使用受控模型重跑。错误重试、会话隔离、旧请求形状、G1 图表选日/筛选回归也经浏览器验证。
8. `browser/lifecycle-*.json` 与 `controlled-http.json` 保存“选定趋势→附加→提问→查询→答案→trace”的完整链。真实模型两题、完整 trace、独立 SQL 复核另存于 `live/`；两题不能代表整套真实模型语义能力，也不替代固定样本验收。

## 边界

只处理单轮每日趋势范围，不处理多附件、单点选日、截图、旧看板金额快照、跨票文档混合或多轮消歧。引用条件加入时固定；数据变更并重建后，答案依据本次查询。受控模型的逐字回答不代表真实模型语义表现。浏览器分别使用无 Key 引擎和受控模型核对生命周期。主会话负责与 G3-02 合并后的独立集成验收。

## 真实样本预算依据

2026-09-27 06:42:23 UTC 核对 [DeepSeek 官方中文价格页](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)：`deepseek-flash` 上下文长度 1M；高峰时段缓存未命中输入 2 元/百万 tokens，输出 8 元/百万 tokens。按 1,048,576 输入与本地 `max_tokens=4096` 上限，峰时全未命中估算 `2.12992` 元/次出站，故先预留 `2.20` 元。30,000 字节仅为请求体大小限制，不能换算成 token 硬上界。完整 usage 才按峰时全未命中价格释放差额；无 usage、超时或不确定状态保留预留。当前仅授权本票总 6 元、最多两次 chat；每 chat 最多六次出站是本票更紧的测试执行限制，并非产品最大调用链承诺。`run_live_samples.py` 使用独立账本、VAR_DIR 和本地代理，真实 Key 只从共享 `.env.live` 只读加载且不写入证据。

两次真实样本均在固定 `64c3291` 发起。第一题“这段时间净营业额是多少？”使用引用的 2026-06-01 至 2026-06-30 / S02，工具 `query_metrics` 查得净营业额 43655.00 元；第二题“7月 S01 的净营业额是多少？”由文字覆盖为 2026-07-01 至 2026-07-31 / S01，查得 30986.00 元。`live/independent-sql-audit.json` 证明两个实际结果与只读 SQL 一致，非仅核对 `answer_type`。账本记录 4 次出站均 HTTP 200、合计输入 12993 / 输出 603 tokens；以官方峰时全部输入未命中价格保守估算本票 0.03081 元，余下本票 5.96919 元。按主会话此前保守累计 1.136358 元相加，第三关累计估算 1.167168 元、总预算剩余 48.832832 元。**这些是 usage 估算，实际提供方账单尚未核实。**所有 `live/` 文本均检查过不含真实 Key；没有额外真实样本或余额/模型列表探测。

## PR #32 独立审查后的路由修正

主会话在固定 `59f6ce1` 上发现两处回归。`route-review-red.txt` 保存新增 2 项失败：`预测模型训练前，请查询S02六月牛肉poke净营业额。` 原本应由 G3-01 的 live 模型解释并调用工具，却在有/无引用时均被过宽的 `intent` 门禁直接拒绝。`credential-review-red.txt` 保存既有 G3-01 凭证诊断测试的 1 项失败：无引用调用被强制改为四参数，注入的三参数诊断写入者没有真正执行。

修正后，无引用请求继续走原有三参数 `_run_engine` 和固定 `plan.kind` 安全名单；趋势的未锚定时间另以 `trend_ambiguous_time` 澄清。对有引用且被启发式误判为 `out_of_scope` 的明确查询，从原问题补足已解析的日期、门店、指标，并在 live 工具入口约束生效条件。明确未知门店、越界日期仍不得借引用变成全量查询。`test_route_regression.py` 保留红灯及 5 项绿色回归，其中一项验证带引用路径的最终凭证脱敏、两项验证未知门店和越界日期不会触发模型。

免费复核：`starter/.venv/bin/python -m pytest docs/verification/g3-06/test_route_regression.py docs/verification/g3-06/test_trend_context.py docs/verification/g3-06/test_live_budget.py docs/verification/g3-01/test_data_chat.py docs/verification/g3-01/test_credentials.py starter/tests -q` → **106 passed**；`starter/.venv/bin/python docs/verification/g3-06/verify_review_routes.py` → 无引用、有引用真实 HTTP 工具链 **2/2**，均有两次受控模型往返且工具结果等于独立 metrics API；请求/响应/trace 见 `review-r1/routes.json`。在当前代码后端 `:8038` 重跑 `G306_MODEL_URL=http://127.0.0.1:9036 G306_EVIDENCE_DIR=../docs/verification/g3-06/review-r1/browser-controlled BROWSER_BASE_URL=http://127.0.0.1:8038 npm run test:browser -- tests/g3-trend-context.spec.ts --workers=1` → **7 passed**。未增加真实模型调用，也未修改旧 G3-01 证据。

## 第二轮复核：早退规划后的明确条件

主会话在 `0c650e7` 又发现启发式 `out_of_scope` 提前返回时，原规划器尚未做门店、商品和时间合法性检查。`early-plan-review-red.txt` 保留 **5 项失败**：显式 `S99` 被静默换成引用 `S02`；`P99` 未被识别；“现在”未明确拦截；“全部时间”内部 `TypeError`；六月/七月比较只保留第一个窗口。

修复在同一趋势解析入口统一使用 `parse_time`、门店/商品目录与当前数据范围：显式未知实体直接结构化拒答；“现在”落在数据范围外时明确拒答；“全部时间”按当前数据全集覆盖引用；两个明确月份且有比较意图时保留两个窗口，并要求模型调用受约束的 `compare_periods`；两个窗口却未说明比较时澄清。服务端对显式商品也约束真实工具参数。测试只增本票文件，不更改原始 G3-01 材料。

字段解析修正后、商品守卫补强前的复核：`starter/.venv/bin/python docs/verification/g3-06/verify_early_plan_http.py` → 网络 HTTP **4 项安全停止 + 2 项真实工具查数**，正确样本由独立 metrics API 核对，完整请求/trace 在 `review-r2/early-plan-http.json`。受控后端 `:8040` 的浏览器 **7 passed**，证据在 `review-r2/browser-controlled/`。随后额外发现模型可在“全部商品”有效条件下擅加 `product_id`，`review-r2/extra-product-red.txt` 保留阻断前的红灯；修复后的工具约束将缺省商品也视为有效条件的一部分。

最终免费复核：`starter/.venv/bin/python -m pytest docs/verification/g3-06/test_early_plan_context.py docs/verification/g3-06/test_route_regression.py docs/verification/g3-06/test_trend_context.py docs/verification/g3-06/test_live_budget.py docs/verification/g3-01/test_data_chat.py docs/verification/g3-01/test_credentials.py starter/tests -q` → **113 passed**（含显式商品、双窗口及缺省商品的工具参数约束）。`G306_REVIEW_BASE_URL=http://127.0.0.1:8041 G306_REVIEW_EVIDENCE_DIR=docs/verification/g3-06/review-r2-final starter/.venv/bin/python docs/verification/g3-06/verify_early_plan_http.py` → 当前代码网络 HTTP **4 项安全停止 + 2 项真实工具查数**；`G306_MODEL_URL=http://127.0.0.1:9036 G306_EVIDENCE_DIR=../docs/verification/g3-06/review-r2-final/browser-controlled BROWSER_BASE_URL=http://127.0.0.1:8041 npm run test:browser -- tests/g3-trend-context.spec.ts --workers=1` → **7 passed**（1280/1440/390）。没有新增付费调用。
