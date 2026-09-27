# G3-05 整体验收：首个固定检查点

- 被测业务提交：`4591fab9a80ef63c440b9a117dbbc4fcbf03c430`（集成 main，2026-09-27）。验收脚本和证据后续提交不改变这个被测源码。
- 环境：macOS 26.7 arm64；Python 3.12.14、Node 24.19.0、npm 12.0.2。`git archive 4591fab` 导出至 `/tmp/moneki-g305-fresh-4591fab`，导出时无 `.venv`、`node_modules`、`dist`、`.env.live`、`clean.db`。该副本中真实创建 venv、`pip install -r starter/requirements.txt`、`npm ci`、`npm run build`、`make rebuild`；清洗保留 18,290 行，索引 35 篇、215 片段。`fresh/input-sha256.txt` 保存输入清单。
- 为保全安装过程的原始终端记录，又独立从同一提交导出 `/tmp/moneki-g305-fresh-proof-4591fab` 并再次实际安装、构建、重建。`fresh/initial-generated-paths.txt` 为空；`pip-install.txt`、`npm-ci.txt`、`build.txt`、`rebuild.txt` 保存完整输出，`platform.txt` 保存版本；两次导出输入 SHA-256 清单逐文件一致。第二份是复现证据，不是把第一次的缓存称为 fresh。
- 独立运行 `starter/.venv/bin/python -m pytest starter/tests -q`：53 passed；评测器测试 260 passed、124 subtests；前端 typecheck/build 成功。

## 未改官方 55 题

两轮均从上述 fresh 源码运行未改的 `eval/run_eval.py` 和 `eval/public_questions.jsonl`，按原顺序逐题发送；真实轮每个多轮 turn 与所有上游往返均保留。历史原 starter mock 17/100、live 25.5/100；第二关 mock 88.5/100，49/55。G3-01 只有定向红灯，没有修复前完整 G3 fresh 基线，不能事后补写为当时基线。

| 固定版本 | 模式 | 得分 | 整题通过 | 原始证据 |
| --- | --- | ---: | ---: | --- |
| 4591fab | 无 Key / mock | 94/100 | 53/55 | `eval-mock/report.json`、`report.md`；失败 H01、H06 |
| 4591fab | DeepSeek `deepseek-flash` / live | **67.5/100** | **40/55** | `eval-live/report.json`、`report.md`、`console.txt`、`chat-trace.jsonl`、`model-traffic.jsonl`、`failure-summary.json` |

真实分类：metrics 6/6、retrieval 15/15、data 12/12、doc **0/16**、version **0/6**、hybrid 15/18、multi_turn 4.5/9、refusal 8/8、safety 6/9、health 1/1。失败整题为 C01–C08、V01–V03、H04、T02、T03（第二轮）、S01。H01/H02/H03/H05/H06 和 T01 在本次真实运行通过。完整 18 个失败 turn 及每条检查见 `failure-summary.json`；不能用总分抵消文档、版本与多轮缺口。

失败 trace 初步分类：10 轮 `document_binding_rejected`（subject_conflict 6、attribute_conflict 4），3 轮模型 `finish_reason=length`，4 轮 `mixed_binding`（含区间方向、价格文档、门店范围），V03 第二轮在首轮拒答清除上下文后变为 clarify。每个具体请求、回答、模型原始消息、检索/工具结果和 trace 已按原样保存；实现修复交回原任务会话，本验收分支不修改业务代码。

## 接入与费用

无 Key health `llm_mode=mock`，配置真实接口后 `llm_mode=live`，快照见两轮 `report.json` 和 `eval-live/health.json`。官方 `eval/llm_gateway.py` 免费预检：P1–P13 PASS、P14 SKIP，32 次本地 chat 均 HTTP 200；假上游 60 次 POST、44 个工具结果，最慢 120.03 秒。P14 因正常场景没有得到可供比较的回答而跳过，见 `preflight/console.txt` 与原始报告；不能称 14 项全通过。

真实轮使用 `run_live_eval.py` 的本地费用守卫。每次实际上游 API（含服务内部重试）发送前先保留 2.20 元；收到完整 usage 才按峰值全输入未命中缓存价格（输入 2 元/百万 token、输出 8 元/百万 token）结算。87 次上游请求均 HTTP 200，usage 齐全；输入 812,593、输出 49,144 tokens，本轮保守估算 **2.018338 元**，连同此前已记录 1.440556 元，G3 累计 **3.458894 元**，50 元授权下剩余 **46.541106 元**。这是按 usage 的保守估算，不是供应商账单；无悬挂预留。脚本只安全读取共享主树已有 `.env.live`，证据没有 Key；Key 字节扫描 0 命中。未做 balance/model-list 探测。

本检查点不代表整票通过。唯一完整真实复验机会留待缺陷修复、独立验收并集成到新固定提交之后；本次原失败材料不覆盖、不删选。

## 后续免费独立验收（仍为 4591fab）

- `controlled-transport/results.json`：当前 typed 数据回答协议的受控上游正常 0.034 秒、正文前四次空白并延迟后 3.265 秒均得到 HTTP 200 `data`；单次模型超时设 2 秒时 2.024 秒返回 HTTP 200 `refusal`，trace 保留技术错误。它验证非流式 HTTP 解析和超时，**不能把官方 P14 SKIP 改写成 SSE PASS**。受控模型只证明传输和程序路径，不证明真实模型语义。
- `browser-mock/`：真实 Chromium 在 1280/1440/390 三种宽度，以可见 AntD selector 鼠标点击（无 `force`、无 JS 改状态）完成 data/doc/hybrid、两轮追问、新对话、数据与文档证据展开、每日趋势引用实际发送，以及 503 后请求体不变的重试。三宽各保存六次成功问答的实际请求/响应和截图；这些是 mock 路径，不是付费模型浏览器结果。
- `replacement/results.json`：只在独立 `/tmp` 副本替换 SQLite 与 KB 并公开重建、重启。原始 SQL 两行（9 份销售、2 份退款）手算得到 7 份、150 元；目标文档 10→6 后，同一实际销量先未达标后已达标，数据证据和 KB-023 引用随输入变化。现行 KB-013 退款期限 24→30 小时后返回 30 小时，历史 2026-06-01 仍引用 KB-012 的 7 天。KB-003 新增“红岩饭”识别为 P06；新增 KB-990 索引 36 篇且检索到，删除重建后索引 35 篇且不再检索到。新增事件的 mock 问答仍 `refusal`，不计语义通过。`replay/` 的受控测试另覆盖 KB md/txt/GBK/html 修改后重建、目标跨边界、事件适用范围、恶意工具拒绝、注入、会话隔离与容量；测试输出必须和独立替换的 HTTP 观察分开理解。
- 初次把两处同名 `test_http.py` 放进一次 pytest 收集，发生模块名冲突；`replay/replacement-tests.txt` 保留该测试运行器错误，随后分别启动独立 pytest 进程得到 G302 6 passed、G303 3 passed。它不是产品测试红灯，也未被从证据中删除。
- **确定性缺陷**：`replacement/scope-defect.json` 在上述数据库再插入 2026-07-01 的 S02/P06 销售 5 份；对“**S02 6月18日红岩饭销量是多少？**”，独立 SQL/精确指标接口均为 6 月 18 日 **7 份**，但 `/api/chat` trace 的 plan 将时间记作“未指定”，实际查询 **2026-06-18 至 2026-07-01** 并回答 **12 份**。只核对前一版替换测试的结果数字会漏掉这个范围错误。完整原始 SQL 行、请求、answer、trace、输入 SHA-256、重建日志均保留；已交原实现任务修复，本验收票不改业务。
- 执行守卫离线检查 `test_live_guard.py` 验证布尔、浮点、缺失、0、超 8192 等配置拒发；1、4096、8192 整数允许；1,048,576 输入及 8192 输出的峰值全未缓存上界为 **2.162688 元 < 2.20 元预留**。该更改只为未来新固定点的受控复验做准备，已保存的 4591fab 真实评测仍是 `max_tokens=4096`，未增付费调用。
