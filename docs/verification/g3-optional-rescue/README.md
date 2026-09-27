# G3 附加抢救：免费重放验证

固定基线 `ee66626d6b48abd0a8ca0e73e6de409e168497c4`，产品提交 `7c7730765fce9fd48c4f67760c60aae4c1e88685`。本节是用户授权的附加修复，不修改 c708 的历史评测、用户原稿或官方 eval。c708 的 94 分 / 52 项通过仍是此前真实模型结果；本补丁没有付费模型复验，不产生新的官方得分。

## 修复与事实更正

- C07 原最终 content 是合法的 `doc`，包含 3 个真实证据 ID。错误在 LiveEngine：因为先前查过 DB，非空 evidence 把它误送入 `render_data`，并非模型最终结构错误。现在按最终 `answer_type` 明确分派，doc 仍核对真实检索身份、原文及范围。3 条所选事实与实际标题上下文共形成 7 条引用。
- H06 原最终选择 `compare_periods`，异常期 `period_b.net_revenue=0`。4 次 `top_k=20` 在工具执行前被验证拒绝，之后 4 次 `top_k=10` 搜索成功，但旧失败永久留在阻断列表。现在仅明确的 top_k 范围验证错误可以被后续真实成功 search 恢复；模型可以改写 query。源执行失败、未知错误及没有后续成功的验证错误仍阻断。原错误 tool 步骤完整保留，额外 `tool_failure_recovered` 记录失败 call ID 与恢复 call ID。检索成功不意味着原因存在：原 facts=[] 输出真实零值数据与“原因无法确定”，沿用既有无文档引用时 answer_type=data 的契约。
- H06 原完整 API trace 为 3,468,308 UTF-8 字节。可逆引用后真实 HTTP 响应为 1,794,510 字节，官方 `eval.run_eval.Client` 的 2MB reader 成功解析，expand 后与原完整对象逐字段全等。

## Trace 引用格式 v1

`TraceStore.get` 只对紧凑 UTF-8 JSON 超过 2 MiB 的 trace 调用去重。普通 trace 保持原形状；内存中仍保存完整 trace，redaction 先于导出发生。没有删除 reasoning、raw response、工具结果、错误、身份或时长，也没有使用 gzip 绕过 reader。

超限对象增加 `_trace_references={"version":1,"references":[...]}`，被引用位置暂存 `null`。每条记录包含 `path`、`target`（字符串键/数组下标组成的路径）和 `encoding`：

- `identity`：从 target 深复制原 JSON 值；仅 tool search_kb result 的 diagnostics/evidence/rejected 与紧邻 search/document_evidence 内容完全一致时替换。比较使用排序键后的 JSON 序列化，避免 bool/int 等 Python 相等但 JSON 不同的值被误合并。
- `json-string`：以 `json.dumps(target, ensure_ascii=False)` 重建字符串；仅 llm_calls.prompt 与 request.messages 的该序列化逐字相同时替换，否则原样保留。

`kbqa.trace.expand_trace` / `kbqa.trace_refs.expand_trace` 返回完整原对象并移除元数据。原 H06 恰有 58 处引用：7 个 prompt 和 51 个重复搜索字段。引用目标本身不会被替换，不形成链或循环。decoder 供可信服务导出的该版本使用，不是任意不可信 JSON 引用解释器。消费者若需要 prompt/重复 tool 字段原形，应先 expand；完整 request.messages 和 search/document_evidence 仍可直接查看。

这是已知结构的无损去重，**不是任意 trace 的通用 2MB 硬上限保证**。若独有数据本身仍超限，仍可能被官方 reader 拒绝；本补丁只证明原 H06 和同类重复结构的改善。

## 验证及复现

来源是 `docs/verification/g3-05/final-c7084d6/eval-live/chat-trace.jsonl` 中 trace `t-20260901-0013` / `t-20260901-0024`。免费重放使用原每轮模型响应及原工具结果；每个工具调用重新查询本地 SQLite / KB，数据结果全等，文档证据除路径相关 evidence_id 外各字段与当前检索一致，然后才保留原 ID 以重放原选择。网络模型入口明确禁止。

```sh
RESCUE_OUT=docs/verification/g3-optional-rescue .venv/bin/python -m pytest docs/verification/g3-optional-rescue/test_rescue.py -q
.venv/bin/python -m pytest docs/verification/g3-01/test_credentials.py docs/verification/g3-02-live-repair/test_selection_boundary.py docs/verification/g3-03/test_mixed.py -q
```

- `red.txt`：产品改动前 3 failed / 2 passed，保存三项原失败。后续将测试中的两个假定改正为既有实际契约：doc 包含标题上下文引用，H06 返回无文档的 data 且结果为 period_b 内字段；没有修改原模型选择或产品结构来迁就测试。
- `green-initial.txt` / `green-second.txt`：开发过程保留；首次恢复规则要求 query 完全一致，原模型实际上改写查询，因此未恢复，后续采用有真实成功搜索证明的检索能力恢复规则。
- `green.txt`：11 项定向通过，含原 C07/H06 重放、伪引用拒绝、已恢复/未恢复/来源失败/未知失败、普通 trace 兼容、非相同字段不去重、原 H06 全对象可逆及真实 HTTP 官方 reader。
- `regression.txt`：92 项现有凭据、文档选择边界、混合协议回归通过。
- `data-regression.txt`：定向原数据引用/伪造/完整 trace 回归。
- `trace-http.json`：实际字节数、引用数、全等结果；测试 HTTP server 已停止，端口不保留。
- `answers.json`：免费重放的实际可见答案与数据/文档依据；`source-manifest.json` 只记录本次依赖的原始文件校验值。

未调用任何付费 provider；未重跑大评测矩阵；未修改 V03、趋势前周、G4 或架构图。复现服务使用隔离临时目录；没有常驻新服务。
