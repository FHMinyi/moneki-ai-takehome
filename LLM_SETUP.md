# LLM 接入说明

## 1. 用了什么

OpenAI 兼容 Chat Completions，Python `httpx`（安装版本见 requirements），没有厂商 SDK。
开发配置为 DeepSeek 官方 `deepseek-flash`；保留厂商默认思考模式，`max_tokens=4096` 包含思考输出，避免短输出额度截断工具规划。思考原文只保留在后端 trace，不展示在回答或聊天证据中。

## 2. 配置从哪里读

`starter/kbqa/config.py` 从环境变量读取 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`，默认均为空。
`LLM_TIMEOUT` 默认 120 秒且上限 120；`CHAT_BUDGET` 默认 150 秒、最大 175 秒。重试最多一次，使用实际已耗时扣减后的预算；至多四轮工具调用、每轮最多六个工具，然后最后一轮回答。每轮模型请求都受整个响应体的总截止时间保护。
不自动读取 dotenv、不在启动时校验 Key 格式、不查余额、不列模型。HTTP 客户端直接连接指定 BASE_URL，不继承系统 HTTP/SOCKS 代理；需要代理时把 BASE_URL 指向明确的兼容网关。

## 3. 怎么换成你们的

1. 在终端设置 `LLM_BASE_URL=https://api.deepseek.com` 和 `LLM_MODEL=deepseek-flash`，安全地设置自己的 `LLM_API_KEY`。不要把 Key 写进命令记录、仓库或前端。
2. 从仓库根目录运行 `make run-live PORT=8000`。三个配置都存在时 health 显示 `live`；缺少任何一个则 `mock`。
3. 修改配置后重启服务即可，不需要重建数据或索引。BASE_URL 保留路径前缀，仅去掉末尾斜杠并追加 `/chat/completions`。

默认 `make run` 仍明确清除模型配置，使用无 Key 模式。首次安装/重建继续按 README 三步流程。

## 4. 怎么看到发给模型的请求

每次 `/api/chat` 返回 `trace_id`，GET `/api/trace/{trace_id}` 可查看 `llm_calls[].request`：完整 model、messages、tools、max_tokens，以及 `response`、`raw_response`、usage、耗时和错误。`steps` 中每个 tool 含实际 params/result/call_id。请求快照独立保存，不随后续消息追加改变；Authorization 不进入 trace，供应商回显 Key 的错误正文也会脱敏。

也可以运行 `python3 eval/llm_gateway.py proxy --help`，按官方网关参数将 BASE_URL 指向代理。代理会真正调用上游并计费，只有用户授权后使用。

结构示例：`{"request":{"model":"deepseek-flash","messages":[...],"tools":[...]},"response":{"choices":[...]},"took_ms":1250}`。Trace 为容量 200 的内存诊断，不持久化；不要把本地诊断服务公开部署。

## 5. 没有 Key 时会怎样

服务仍启动。health 报告 `mock`；metrics 使用真实只读清洗库；retrieve 使用真实知识库索引；chat 使用已有保守规则降级路径，正常返回 data/doc/hybrid/refusal/clarify。模型调用失败时返回 HTTP 200 的 refusal 并留下真实错误，不静默转成成功的 mock 回答。

## 6. 依赖与安装

沿用 `starter/requirements.txt`，无需额外模型下载或新检索服务。`make setup` 安装后端和前端依赖，`make rebuild` 重建本地数据/索引和前端。启动加载本地索引，不联网请求模型；实际启动时间取决于首次重建和文件系统。

## 7. 自测结果

原始官方预检：`python3 eval/llm_gateway.py preflight --service-url http://127.0.0.1:8033 --port 9033 --no-wait --out docs/verification/g3-01/preflight`。
测试服务用预检工具打印的三个环境变量，通过 `make run-live PORT=8033` 启动。

结果：**13 PASS，1 SKIP（P14）**。原始输出见 `docs/verification/g3-01/preflight/preflight_report.md` 和 JSON，首轮系统 SOCKS 环境故障的报告保存在 `preflight-first`，未覆盖。

P1—P13 通过：路径前缀、模型/Key、参数、输出额度、无探测、工具消息、JSON响应、失败拒答、思考不泄漏、总时限、live health、reasoning_content原样回传。
P14 未检查：官方假模型的固定最终自由文本不符合本票数据回答的调用/指标引用 JSON，normal 和 slow 都拒绝该不受约束的数字表达，因此官方工具无法对照业务回答。没有修改评分工具或放松产品校验。
补证命令 `starter/.venv/bin/python docs/verification/g3-01/verify_keepalive.py`：同一合法工具调用和最终 JSON，normal 与 slow 仅 HTTP 节奏不同；slow 每个模型响应先发送 18 秒真实空行，两次往返后 `/api/chat` 给出同样的真实数据与证据。另用 12 秒总预算证明持续空行仍超时并返回 refusal。原始请求/响应/trace/耗时见 `keepalive/`。这属于独立补证，不将官方 P14 改写为 PASS。非流式产品不适用 SSE 展示。

## 8. 已知限制

G3-01 验证完整单轮查数、区间比较、会话存储隔离和聊天交互。纯数据最终输出要求模型返回实际工具调用 id 与指标字段，代码从结果生成标签和数值；错误引用、任意数值散文或超过契约容量的证据会明确拒答。此时可缩小条件重试。
文档来源、混合分析、多轮语义继承和显式趋势引用仍由 G3-02/03/04/06 交付；保留原无 Key 已验收能力和响应字段，不以本票受控模型测试证明这些真实模型能力。会话最多 500 个、每会话六轮，无 ID 不存历史，不跨重启持久化。真实调用结果以本票 live 记录和验收回执为准；旧 live 25.5 分不是修复后结果。

G3-01真实接入补记：首次f991720因为模型将工具名误作call_id拒答；354f6d4显式回传ID后，相同查数与区间比较两样本成功，并由独立SQL核对。累计3chat/6API（包含失败），详见docs/verification/g3-01/live；最终1608043增加缺项澄清格式，只经受控验证。0.047028元是高峰未命中保守估算，不是账单确认。完整第三关真实评测仍待G3-05。

PR30凭证修正：此前仅LLM记录回调脱敏，HTTP200非JSON异常详情与异常链仍可能泄漏上游回显Key。现统一处理错误边界、Trace记录与最终序列化、session/API响应以及服务兜底日志；异常不携带原始cause/context，日志使用已脱敏traceback。Key清洗先于预览截断。保留正常完整诊断和有用错误原因；回归见test_credentials.py及credential-regressions.txt。
