# G3-01 验收映射

权威规格：GitHub #24；固定基点 `2839c674dc2fe66bf52265cb58aafb5b3452182a`。
执行配置：GPT-6 Astra / medium。原输入、评测器、历史证据与既有未跟踪材料的 SHA-256 见 `protected-before.json`。

| 验收项 | 实现边界 | 计划证据 |
|---|---|---|
| 1 启动/配置 | 根 Makefile、config、LLM_SETUP | 无 Key health、受控地址/model/auth、无启动请求 |
| 2 工具许可 | toolspec、Service.run_tool | run_sql/未知工具/额外参数/类型/日期/实体拒绝，数据库哈希 |
| 3 数值来源 | live 数据回答绑定真实调用及指标，render | 真实 HTTP 查数/比较、独立 SQL 核对、替换数据；错误指标/伪造数字攻击 |
| 4 live 路由 | Service._run_engine 的规则与模型边界 | 规则误判仍进入 live，破坏性请求先拒绝，短追问澄清 |
| 5 协议/预算 | LLMClient、LiveEngine | 官方免费预检、额外 400/超时/重试预算检查 |
| 6 trace | LLMClient、Trace、工具执行 | 完整请求/原始输出/工具结果/错误/耗时、凭证脱敏 |
| 7 聊天 UI | 独立 ChatSidebar，保持看板筛选所有权 | 1280/1440/390 实际浏览器，发送/等待/重试/证据/旧响应隔离 |
| 8 session | 有界 SessionStore、前端新会话 | 交错会话的真实模型请求不互见，无 ID 不存共享历史 |
| 9 回归/红绿 | 新缺陷探针、原回归/公开题库 | 修复前后原始输出、无 Key 49/55 基线及前两关回归 |

真实付费验证：第三关累计 50 元；本票最多 10 元且最多 6 次 chat。免费预检通过后，先回报可核实定价和保守费用上界，再在既有授权内执行。工具往返与重试均计费。当前尚未调用。

G3-02 文档来源重构、G3-03 混合推导、G3-04 多轮语义、G3-06 趋势引用不在本票中。单轮查数通过不能证明这些后续能力。

## 证据时间边界

修改业务前，在固定2839c67业务字节上，只于2026-09-27 12:50:42运行了新增test_data_chat.py，结果9F/1P；红灯提交3686878。当时没有重跑完整55题、53后端、199 RAG、免费preflight或真实模型。第二关既有结果只作为历史参照。此目录后续green/backend/rag/no-key-eval/preflight/browser等均为修改后的证据，不称作第三关完整前置基线。

## 已执行检查点

- 单元/边界探针16通过；真实HTTP原库+独立手算替换库12项通过（最终另补2项路由）。
- 原后端53、真实RAG199通过；无Key完整公开评测88.5/100，49/55，与历史已验收行为保持。
- 官方免费预检13PASS/1SKIP（P14），原报告保留。独立 /api/chat normal/slow合法结果协议完成同样真实查数；slow两轮共36秒空行，12秒总预算场景refusal，详见keepalive/result.json。
- 受控浏览器4项通过，覆盖1280/1440/390及会话/重试生命周期。首轮选择器未匹配Ant两字按钮的空格，补显式发送aria-label；失败记录保留。
- 保护清单3066文件当前全部保持。

原始命令记录位于各脚本与输出；后续固定被测提交、真实调用、资源和最终验收状态在交付时补记。

## 最终自验回执（等待主会话独立验收）

最终业务提交 `1608043`；完整文件SHA见 `tested-tree.json`。真实失败样本固定 `f991720`，调用ID修复后的真实成功样本固定 `354f6d4`；其后 `1608043` 仅增加无数据的clarify/refusal结构，真实澄清语义未新增付费验证。文档/验证产物后续提交不改变业务字节。

| # | 自验结果 | 证据 |
|---|---|---|
| 1 | PASS | 默认make run无Key；显式run-live使用环境；preflight P1—P6/P12；真实provider/model及usage见live/；LLM_SETUP八节 |
| 2 | PASS | toolspec不声明SQL且入口拒绝SQL/未知/写工具；严格参数；19→20探针、forged-*、preservation；原只读保证保持 |
| 3 | PASS（本票范围） | http/original/compare与手算replacement-*；live/chat-2、chat-3、audit；字段/ID伪造与同工具两调用隔离探针 |
| 4 | PASS（受控） | http/rule-bypass：旧planner=refusal/out_of_scope，完整经营问题仍进入真实工具；safety/short/model-clarify；真实泛化能力仅有两条样本 |
| 5 | PASS，官方P14保留SKIP | 官方13PASS/1SKIP；keepalive/的完整normal/slow/budget对照（实际数值/证据/trace）补证；400与原预检错误码/畸形参数/空内容/超时；有界重试 |
| 6 | PASS | 每次HTTP证据中的完整request/response/raw_response/usage/took_ms，tool参数与结果；超4000字探针；Key回显脱敏；浏览器未显示思考 |
| 7 | PASS | browser-final.txt四项；1280/1440/390视口截图，实际请求/响应、展开证据、长输入、等待禁重复、503重试、新会话丢弃旧响应 |
| 8 | PASS（隔离，不含多轮语义） | session深复制/500会话/6轮上限探针；http/interleaved/short；browser生命周期请求session不同 |
| 9 | PASS（已验收行为保持） | 53后端、199真实RAG、完整原55题88.5/100、49/55；原前端23+附加3=26，replacement3、empty3；新增聊天4；红灯证据及各提交 |

相关命令：

```bash
starter/.venv/bin/python -m pytest docs/verification/g3-01/test_data_chat.py -q
starter/.venv/bin/python docs/verification/g3-01/verify_http.py
python3 docs/verification/g3-01/verify_routes.py
starter/.venv/bin/python docs/verification/g3-01/verify_keepalive.py
python3 docs/verification/g3-01/verify_dashboard.py
BROWSER_BASE_URL=http://127.0.0.1:8032 npm --prefix frontend run test:browser -- g3-chat.spec.ts --workers=1
starter/.venv/bin/python -m pytest starter/tests -q
starter/.venv/bin/python -m pytest docs/verification/g2-01/test_ingestion.py docs/verification/g2-02/test_evidence.py docs/verification/g2-03/test_retrieval.py docs/verification/g2-04/test_doc_qa.py docs/verification/g2-04-heading-fix/test_heading.py -q
python3 eval/run_eval.py --base-url http://127.0.0.1:8031 --questions eval/public_questions.jsonl --out docs/verification/g3-01/no-key-eval
```

verify_http/keepalive需要先按controlled_model.py启动9032并用该地址启动8032（dummy Key/model，真实本地库）。原前端23项脚本默认会写历史截图路径，今后必须通过G1 run_browser.sh提供所有输出环境变量或在隔离源码导出中执行。本轮不再重复覆写：首次34张覆盖已另存original-browser-screenshots并从2839c67恢复；preservation.json同时证明固定提交与原SHA相同，最终3066保护文件0差异。这一过程错误保留，未以恢复后的0差异掩盖。

### 真实样本与费用

官方定价原文URL/时间/摘录见pricing-source.json。高峰全部输入按未命中2元/百万、输出8元/百万计保守估算。执行代理每次出站（含重试）先预留2.20元，覆盖官方1M上下文按1,048,576计算加4096输出的最坏额度；完整usage才结算释放，无usage不释放。UTF8大小仅作请求长度限制，不宣称token硬上界。

累计3chat、6API、输入18,834token、输出1,170token；0.047028元为保守估算，非账单确认；无悬挂预留，本票10元额度剩余9.952972元。失败chat-1不删除，复验chat-2/3通过独立SQL：六月qty417，六月净额15889，七月13635，差额-2254、-14.19%。真实样本已停止，未用额度交主会话回收；没有全量真实55题评分，也没有部署。

### 自审与限制

自审发现并修复call_id可见性、澄清类型；保留严格引用，不接受工具名或自行数值。业务diff范围为11个入口/模块和聊天组件，未改原输入/评分器。前两关无Key能力保持；live文档事实语义、混合输出、多轮继承及趋势引用仍待后续票，不能据两条真实data样本宣告第三关完成。容量超出契约的查询结果当前拒答并提示缩小范围；没有流式或完整trace面板。

没有在修改前运行完整第三关起点：只记录2839c67业务字节上的新增9F/1P，其他完整检查是修改后运行。G2历史分数只作参照，不能作为本票前置重跑证据。

最终1608043上重新运行53后端、199真实RAG、55题无Key，见backend-final.txt/rag-final.txt/no-key-final；此前输出继续保留。新调用ID修复不改变mock路径，仍以实际重跑建立最终固定提交对应。

## PR30 P1复审修正

主会话固定fb214b6拒绝验收：上游HTTP200非JSON正文回显凭证时，原llm_calls已脱敏，但bad_json异常详情/异常链/最终trace仍泄漏；原测试未覆盖这一边界，前文初次PASS结论因此不充分。新增红灯提交def4475为6F/2P，保留credential-red.txt。

修复覆盖统一凭证清洗、LLM异常详情及cause/context、最终Trace序列化、session/API输出与兜底日志；先清洗再截断，保留错误类型/状态码/非敏感详情与正常完整trace。验证命令：

```bash
starter/.venv/bin/python -m pytest docs/verification/g3-01/test_credentials.py docs/verification/g3-01/test_data_chat.py starter/tests -q
```

10项凭证回归+20项查数/协议+53原后端，共83通过。HTTP200坏JSON用真实本地HTTP假上游回显假Key，FastAPI TestClient经过真实chat/trace路由；相邻timeout/transport/unexpected/finish/HTTP错误、异常链、最终输出及捕获日志也检查。正常完整请求/响应和长诊断保留。没有真实模型复验和新增费用。

非阻塞UX限制：展开证据目前直接展示JSON；消息变化时聊天列表会滚到底部，查看较早历史的体验仍可改进。按主会话要求留待后续证据展示工作，本次不扩大修复。
