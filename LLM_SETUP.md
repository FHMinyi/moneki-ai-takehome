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
G3-02 的单轮文档使用检索证据 ID 与原文摘录；混合分析、多轮语义继承和显式趋势引用仍由 G3-03/04/06 交付；保留原无 Key 已验收能力和响应字段，不以本票受控模型测试证明这些真实模型能力。会话最多 500 个、每会话六轮，无 ID 不存历史，不跨重启持久化。真实调用结果以本票 live 记录和验收回执为准；旧 live 25.5 分不是修复后结果。

G3-01真实接入补记：首次f991720因为模型将工具名误作call_id拒答；354f6d4显式回传ID后，相同查数与区间比较两样本成功，并由独立SQL核对。累计3chat/6API（包含失败），详见docs/verification/g3-01/live；最终1608043增加缺项澄清格式，只经受控验证。0.047028元是高峰未命中保守估算，不是账单确认。完整第三关真实评测仍待G3-05。

PR30凭证修正：此前仅LLM记录回调脱敏，HTTP200非JSON异常详情与异常链仍可能泄漏上游回显Key。现统一处理错误边界、Trace记录与最终序列化、session/API响应以及服务兜底日志；异常不携带原始cause/context，日志使用已脱敏traceback。Key清洗先于预览截断。保留正常完整诊断和有用错误原因；回归见test_credentials.py及credential-regressions.txt。


G3-02 文档协议：`search_kb` 的 `evidence` 给出 `evidence_id/doc_id/chunk_id/quote/source_start/source_end/scope/metadata/context`。source 位置基于 loader 解码后的可见正文（HTML 去标签、GBK 解码），不是原始文件字节偏移；ID 包含索引内容键，重建后旧 ID 不可复用。适用日期/门店来自原问题的 plan，检索改写不放宽它。模型最终只提交 `{"answer_type":"doc","facts":[{"evidence_id":"..."}]}`，一至四条；程序原文摘录或按真实表头渲染，不接收任意改写陈述、quote 或数值。没有支持证据时应返回 refusal。保留完整检索过滤/证据集合/模型往返/绑定诊断。已有 mock 文档取证也通过同一证据集合校验身份，但其既有保守语言规则不成为 live 的通用否决器。

主体实体、已知封闭问题属性及明确单位检查是有界保护，不是任意语言的完整语义蕴含证明。live 单轮采用摘录式回答；它可能保守拒答、选取不够精炼的原文，不能据受控通过声称模型理解全面正确。实际付费样本与失败保存在 `docs/verification/g3-02/live/`（尚未执行时该目录不存在）。


用户于2026-09-27明确将工具轮数上限从4调整为6：最多执行6轮工具，每轮最多6个工具调用，随后还有一次模型最终回答机会；该次再请求工具会拒绝执行。默认总耗时150秒（配置硬上限175秒）、单次请求至多120秒、暂时故障最多重试一次不变。重复检索只向模型提供新增的、按原文与适用scope绑定的证据；完整诊断留trace。G3-02前三自然样本在b62e6dc通过；身份证负例在b62e6dc触发本地尺寸保护、b37af3d触发tool_loop，均非语义拒答成功。后续单次六轮复验结果按本票live/chat-6.json及README记录；完整第三关验收仍须带上此负例。


G3-02最终阶段修正：此前第7次请求仍为tool_choice=auto，这让模型无法明确知道必须收尾。当前在第6轮工具完成后，同一第7次调用设置tool_choice=none，并要求只按已有证据返回既定JSON；不足时诚实refusal，不把上限推断成资料不存在。原工具声明保留以兼容既有tool消息，reasoning_content仍原样；none随原生重试保留。供应商违约toolcalls在执行前拒绝。总回合、工具轮数、超时与重试次数均不增加。该修正已受控HTTP验证，尚无新真实样本；不能把chat6原失败视作本修正后结果。


最终授权chat7实际在第4次auto请求较早返回refusal，未执行none阶段。原始模型说明缺少身份证要求依据，但带v2/KB-013，触发现有拒答数字校验，最终data_binding失败提示；端到端负例仍未验收。当前PR明确留此协议兼容性待审，未擅自放宽校验；不把此前失败或受控none测试说成真实全面通过。最终本票7chat/25实际API、保守估算1.089330元（非账单），真实调用已停止。


PR31 R2协议修正：拒答输出使用`{"answer_type":"refusal","reason":"insufficient_evidence"}`，代码渲染固定的当前依据不足说明。不能在refusal里附政策断言/概括/编号；政策事实必须选择doc证据。为旧模型输出兼容`answer_type:refusal,answer:...`时，只解释refusal状态，整段answer均不展示，原文保留trace；这不是放宽数字校验或删数字。真实工具失败、网络错误等仍是技术错误，不转换为“资料不存在”。chat7免费完整回放可用该状态安全收尾，未新增真实调用。R1开放问句支持性缺口仍待设计/修正，当前不能视作整票通过。


PR31 R1选择协议进一步明确：每个facts元素必须同时有evidence_id和binding，binding含subject/attribute两个锚点数组及value。锚点记录question逐字片段、source（quote、context数组下标；主体也可title）与text真实来源文字；value记录kind/question/text，复用既有时长/金额/时间等形状。禁止只给subject_supported布尔值。系统核实ID、原文位置、范围和可定位主体/属性冲突；元信息标题标metadata.title、不当正文offset。未新增模型核对阶段，普通文档仍在原工具/最终选择回合完成；同义/英汉语义解释仍由本次模型负责，代码不提供通用蕴含证明。控制器正反与替换已免费验证，新选择协议尚未新付费测试；旧真实结果和chat7免费回放分开记录。


PR31第二轮审查进一步限制非事实状态：clarify使用`{"answer_type":"clarify","missing_fields":["date_range","store"]}`，允许date_range/store/product/metric/question，代码生成中性问题，不接受额外政策正文；旧自由answer仅兼容状态及已知字段标签，正文不展示。doc属性必须锚定业务动作/属性，不能只把多久对应24小时；value另记录量型。时长焦点之后明确业务谓词不能省略，主体不能由功能成分冒充。没有新增模型阶段或付费；合并趋势main后的交叉验证另列。
