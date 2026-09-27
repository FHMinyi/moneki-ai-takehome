# 现场调试：把一次问答的证据交给 AI

可以让 Codex 直接读取本地 trace JSON 和源码；也可以把脱敏后的必要片段作为附件或粘贴进对话。**先保存原始文件，再请 AI 诊断**，不要只复制一段最终回答，也不要粘贴 `.env.live`、Key 或整份知识库。trace 已做凭证脱敏，分享前仍应检查其中的业务数据范围。

## 复现和取证

1. 在相同提交、输入数据/知识库、模型配置和会话条件下重新提问；记录原始问题、`session_id`、是否带 `context`、回答与 `trace_id`。多轮题按原顺序重放，不把新会话当旧会话。重建后必须重启服务。
2. 在该服务**重启前**用响应里的 `trace_id` 保存原始 trace：

   ```bash
   TRACE_ID='替换成这次回答的trace_id'
   curl -fsS "http://127.0.0.1:8000/api/trace/$TRACE_ID" > /tmp/moneki-trace.json
   git rev-parse HEAD
   curl -fsS http://127.0.0.1:8000/api/health
   ```

3. 同时记录：实际回答、独立预期和依据（原始 SQLite 只读查询或 KB 连续原文）、提交 SHA、`llm_mode`/模型名/输出上限（不含 Key）、重建与重启状态。先检查 trace 的最终条件、检索候选与过滤理由、工具参数和结果、模型请求/原始响应、耗时及 errors，定位是哪一层与预期分叉。
4. 把这些本地文件路径与下面的提示词交给 Codex。请它**先诊断并列最小复现，不立刻改代码**；确认原因后增加最小行为测试，修复同一调用路径，再跑该测试、相关回归和未改官方评测。自建题和官方 55 题结果分别保存。

可复制的提示词：

> 请读取 `/tmp/moneki-trace.json`、当前仓库源码和下面的独立依据。先按请求→规划/会话→检索/工具→模型输出→最终回答逐步定位第一个分叉，标出可核对的 trace 字段和源码位置。不要先改代码，不要把返回 HTTP 200 或引用合法当作答案正确。给出一个最小复现、预期和实际；确认后再提最小修复与需要跑的回归。问题：`<原问题>`；session/context：`<原请求>`；实际：`<实际回答>`；预期及独立依据：`<只读 SQL 结果或 KB 原文>`；提交：`<SHA>`；health/模型配置摘要：`<无 Key 的摘要>`。不得读取或输出 `.env.live`、Key、cookies。

## 一条已经保存的真实失败

首个第三关集成版本 `4591fab` 的真实模型 C01 问“外卖订单多久内可以申请退款？”。模型确实检索到 KB-013“外卖订单在送达后 24 小时内提出”，却因旧主体/属性字面绑定把“申请退款/提出”判为 `attribute_conflict`，最后 `refusal`；原请求、模型选择和 `document_binding_rejected` trace 见 [G3-05 首轮逐轮文件](verification/g3-05/eval-live/chat-trace.jsonl)（chat 7）。后续 G3-02 在独立任务中按用户确定的边界改为由同次模型选择语义，代码继续核实真实证据 ID、原文位置和确定性范围；修复证据见 [G3-02 回执](verification/g3-02-live-repair/README.md)。旧真实失败不会因为修复后受控回放通过而变成旧运行成功；最终新固定点的真实模型结果须看 [评测报告](../EVAL_REPORT.md)的独立一轮。

优先使用已有最小测试和官方脚本：问题对应的 `docs/verification/g3-02-live-repair/` 或 `g3-03-live-repair/` 定向测试，及 `python3.12 eval/run_eval.py --base-url http://127.0.0.1:8000 --questions eval/public_questions.jsonl --out /tmp/新的独立目录`。真实模型评测会产生费用，只在获授权预算内执行；平时先用无 Key/受控路径复现确定性问题。本流程不依赖新增调试面板或回放平台。
