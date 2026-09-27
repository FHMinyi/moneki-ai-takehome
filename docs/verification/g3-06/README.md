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

浏览器服务使用独立 `VAR_DIR=/tmp/moneki-g306-browser-var`、端口 8036、无 Key；受控服务使用独立 `/tmp/moneki-g306-live-var`、端口 8037 与本地模型端口 9036。截图与逐宽度 HTTP/trace 在 `browser/`、`browser-controlled/`，第一关趋势回归截图在 `regression-daily/`。测试输出不覆盖历史证据。

## 八项验收映射

1. `DailyTrend` 只在有效响应的首尾日期与当前生效筛选一致时显示“加入提问”；引用整块日期、门店和固定净营业额指标。浏览器在选中中间日期后验证引用仍为完整范围，并覆盖加载错误状态。
2. `ChatSidebar` 的待发引用最多一张；删除、替换、筛选草稿变化、已发消息固定范围、重试携原引用、新会话清空与迟到请求丢弃由 `g3-trend-context.spec.ts` 验证。
3. `context` 可选且仅接受 `daily_trend` 的五个字段。`test_trend_context.py` 覆盖额外 SQL/工具/金额字段、无效日期/门店/类型的 HTTP 200 结构化拒答和旧两字段请求。
4. `context_resolution` trace 记录有效条件、每字段来源与覆盖；单轮“这段时间”使用引用，明确七月 S01 使用文字新条件，“这一周”要求澄清。HTTP 与受控样本均检查。
5. 受控 HTTP 的 `data_evidence` 等于独立 metrics API 同条件结果；测试复制原始 SQLite、修改一条有效销售金额、重建到另一个独立 `VAR_DIR`，同一引用的净营业额随之增加 1000 元。
6. `request`、`context_validation`、`context_resolution`、`plan`、`tool` 与模型请求/输出保存在 trace。`replay_controlled.py` 保存可重放原请求，且同条件结果与实际工具一致。
7. 1280、1440、390 的真实 Chromium/后端/数据库证据见 `browser/lifecycle-*.json` 与截图；同一路径还在 `browser-controlled/` 使用受控模型重跑。错误重试、会话隔离、旧请求形状、G1 图表选日/筛选回归也经浏览器验证。
8. `browser/lifecycle-*.json` 与 `controlled-http.json` 保存“选定趋势→附加→提问→查询→答案→trace”的完整链。受控模型结果仅证明工具/约束/证据路径；真实模型结果另行记录，不以其代替固定样本验收。

## 边界

只处理单轮每日趋势范围，不处理多附件、单点选日、截图、旧看板金额快照、跨票文档混合或多轮消歧。引用条件加入时固定；数据变更并重建后，答案依据本次查询。受控模型的逐字回答不代表真实模型语义表现。浏览器分别使用无 Key 引擎和受控模型核对生命周期。主会话负责与 G3-02 合并后的独立集成验收。
