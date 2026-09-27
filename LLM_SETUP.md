# LLM 接入说明

## 1. 用了什么

OpenAI 兼容 Chat Completions，Python `httpx`（安装版本见 requirements），没有厂商 SDK。
开发配置为 DeepSeek 官方 `deepseek-flash`；保留厂商默认思考模式。首个第三关集成固定点 `4591fab` 使用 `max_tokens=4096`（含思考输出），完整真实评测发现 3 轮 `finish_reason=length`。最终修复集成 `c7084d6` 使用 **8192**，独立原 55 题真实复验为 94/100、52/55；不能回写旧轮。思考原文只保留在后端 trace，不展示在回答或聊天证据中。

## 2. 配置从哪里读

`starter/kbqa/config.py` 从环境变量读取 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`，默认均为空。
`LLM_TIMEOUT` 默认 120 秒且上限 120；`CHAT_BUDGET` 默认 150 秒、最大 175 秒。暂时性上游故障最多重试一次，使用实际已耗时扣减后的预算；至多**六轮**工具调用、每轮最多六个工具，然后还有一次只作最终回答的模型机会。每轮模型请求都受整个响应体的总截止时间保护。
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

在首个第三关集成固定点 `4591fab`，原样运行官方 `eval/llm_gateway.py preflight`，结果 **P1–P13 PASS、P14 SKIP**。P14 的官方假模型最终自由文本不符合当前 typed 业务输出，normal 场景未拿到可对照的回答；没有修改官方预检。原报告见 [G3-05 预检](docs/verification/g3-05/preflight/preflight_report.json)。另用相同 typed 工具与最终结构做普通、正文前空白延迟、超时的**非流式 HTTP**补证，见 [传输记录](docs/verification/g3-05/controlled-transport/results.json)；它不等于官方 P14/SSE 通过。

最终集成 `c7084d6f841d150c6672410719a4785b4a7696b1` 的 DeepSeek `deepseek-flash` 配置：`LLM_BASE_URL=https://api.deepseek.com`，`LLM_MODEL=deepseek-flash`，默认思考，`max_tokens=8192`。评测通过本地逐请求费用守卫代理到官方接口；实际 Key 只从环境进入后端进程，不在仓库、前端、trace 或报告中。完整未改官方原 55 题真实运行 **94/100、52/55**，每次请求/响应、工具、完整 usage、失败和逐轮 trace 在 [最终 G3-05 记录](docs/verification/g3-05/final-c7084d6/README.md)。这是一次固定版本观察，不是隐藏题或长期稳定性保证。

每次实际出站 API（含重试）发送前保留 2.20 元，收到完整 `prompt_tokens` 与 `completion_tokens` 才按高峰全输入未命中价格结算；缺 usage 保留预留，不用字节数推测 token 上界，也不调用余额或模型列表。最终全题 102 API 都有 usage，估算 2.755886 元；加此前阶段与一次真实浏览器定向，第三关累计 6.537374 元，50 元授权下剩余 43.462626 元、无悬挂预留。费用是保守估算，**不是供应商账单**。

## 8. 当前回答协议与已知边界

文档工具 `search_kb` 返回真实检索池的 `evidence_id`、文档/片段 ID、连续原文位置、适用 scope 与标题上下文。当前模型最终可用 `{"answer_type":"doc","facts":[{"evidence_id":"本次工具实际返回的ID"}]}` 选择一至四条原文；程序核对 ID、原文位置、确定性日期/门店适用范围并从原文渲染，不接受模型自造的 quote、数字或数据库结果。自然语言片段是否真正支持用户所问主体/属性，由**同一次模型选择**，不是代码对任意语义的完整证明。检索改写不能放宽原问题的确定范围；数据库数字必须经过只读白名单工具和代码计算。拒答或澄清使用受约束状态，不向用户展示自由政策断言。工具最多六轮、每轮六个调用，随后一次最终回答机会；真实工具错误与资料不足分别记录在 trace。

最终真实评测未全通过 **C07、V03、H06**：C07 的模型结果绑定无效而技术拒答，V03 第二轮检索后仍选择依据不足，H06 混合核验失败且 trace 超过官方 2 MB 上限。一次真实浏览器退款到账负例在模型两次 `search_kb(top_k=15)` 超工具上限后技术拒答，不能证明它理解申请时限与到账时间的区别；带趋势引用的“比前一周低”比较在免费受控 HTTP 中被范围守卫拒绝，未发送真实模型请求。详情与原始失败见 [最终报告](EVAL_REPORT.md)和 [验收目录](docs/verification/g3-05/final-c7084d6/README.md)。无 Key 模式、受控模型和真实模型证据不能互相代替；trace 是内存诊断，重启前应保存。

## 9. 历史协议记录

G3-01 的单轮接入、G3-02/PR31 曾尝试的逐字主体/属性 `binding`、封闭属性与单位硬门槛、以及当时“R1 待设计”的文字，均为**历史过程，已由 PR #36 的当前最小 `evidence_id` 选择协议替代**，不再是本版接口要求。旧轮的 4096 输出和 67.5/100、40/55 真实成绩保留用于前后对照，不把新代码的通过追认到旧版本。设计取舍、红绿证据和保留的反例见 [G3-02 修复证据](docs/verification/g3-02-live-repair/README.md)、[调试记录](DEBUG_LOG.md)与 [首轮 G3-05 原始结果](docs/verification/g3-05/README.md)。现场定位错答可按 [trace 调试流程](docs/DEBUG_WORKFLOW.md)把本地脱敏 JSON 与源码交给 Codex；不要复制 `.env.live`、Key 或整份知识库。

用户追加授权后，在 trace 补丁 `5b6a4ca` 又独立执行**一次**完整真实 55 题：同为 `deepseek-flash`、默认思考、`max_tokens=8192`，结果 **94/100、53/55**；H05 内容覆盖不足、S01 最终类型无效，见 [追加复验](docs/verification/g3-05/optional-5b6a4ca/README.md)。本轮 91 次 API usage 完整，新增保守估算 2.252672 元，第三关累计 8.790046 元、余 41.209954 元，非账单。此结果不覆盖 `c7084d6` 旧轮 C07/V03/H06 失败，也不证明输出稳定性。
