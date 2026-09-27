# G3-02 验证记录

> **PR31最新审查修正：** 红灯d44b4e0、R2修复b6299b5、R1同次锚点修复eb7cad4已追加。固定回归169后端、49真实HTTP、4浏览器通过；chat7免费完整回放安全呈现依据不足。未新增模型阶段/付费；新协议仍待主会话独立核验，不声称新真实调用或通用蕴含证明。详见[审查增量证据](review-r1-r2/README.md)。下文先前未通过记录和原真实失败保留。

起点：`587ae820185cd10839e189efa9fb2ed8863d1ca5`。这是本票修改前定向检查，不是第三关整体前置 baseline。

修改前命令：`starter/.venv/bin/python -m pytest docs/verification/g3-02/test_document_binding.py -q`。结果：8 failed / 1 passed，原始输出 `before.txt`；其中4项复现旧版本/近主题错误陈述可被交付，4项新证据协议尚未实现；48小时无依据数字原本即被拒绝。

测试使用受控模型输出和真实检索，不证明真实模型理解能力。原输入、评分器、历史证据及既有未提交材料共2434文件sha256见 `protected-before.json`。

记录时间：2026-09-27T05:47:50.699329+00:00

## 交付结论与固定点

实现、受控验证与原能力回归已完成，**真实“退款是否要求身份证”负例仍未通过，需主会话决定是否阻塞本票验收**。不得把最终refusal类型等同语义正确；当前票必须先由主会话审查收尾协议修复及真实验收缺口；不能直接把它转交G3-05当作本票完成。后续整体验收也应保留该负例。

| 固定点 | 含义 |
|---|---|
| `587ae820185cd10839e189efa9fb2ed8863d1ca5` | 实际审查起点，G3-01合并后main |
| `ededc76` | 本票定向红灯，9项8F/1P；不是第三关整体前置基线 |
| `b62e6dc` | 共享文档证据、来源UI与结构化选择；真实chat1–4 |
| `b37af3d` | 模型只传evidence/scope，按scope+原文身份去重；真实chat5 |
| `437aac1` | 用户指定工具执行轮数4→6；真实chat6 |
| `2dbd863` | 主会话复审修正第7次最终请求tool_choice=none与明确收尾，最终业务固定点；实际chat7较早结束，未触发none阶段 |

实现提交曾因临时提交消息复用而以错误标题形成 `e3c574c` 并推送，随后在仅本任务分支 amend 为 `b62e6dc`，使用force-with-lease纠正标题/正文并去掉末尾多余空行。没有改动其他分支。之后所有修复均追加提交，保留所有已出示固定点。`fixed-source.json`、`fixed-source-437aac1.json`及`fixed-source-2dbd863.json`记录各业务固定点源码哈希；最后证据提交不再改业务。

## 七项验收映射

| #25验收项 | 结果与证据 |
|---|---|
| 1 真实检索集合、身份/位置/范围 | 受控通过。`DocumentEvidence`只从eligible/nonzero/nonpadded hit生成原文跨度，ID含索引内容键、chunk、位置和scope；未检索/旧版本/伪造ID不能补引。`test_only_genuine_retrieval_can_create_evidence`、`test_no_search_no_citation`、`test_scope_is_part_of_evidence_identity`；trace的search/document_evidence/document_binding。mock原选择经同一pool校验，后续混合可复用，但未改混合路径。 |
| 2 陈述与主体/属性、连续quote、格式 | 受控通过。模型仅选facts/evidence_id，代码摘录原文或按真实表头渲染，不接收额外answer/quote/数值；有限实体/封闭属性/明确单位检查。`test_real_nearby_span_not_sufficient`、`test_unbound_claims_rejected`、`test_no_forged_id_or_borrowed_claim`；`http-compact/`和`http-six-rounds/`中MD/TXT/GBK/HTML、原199局部标题/无标题保证。此边界不是任意中文蕴含证明。 |
| 3 当前/历史/销售区间外/门店 | 受控通过；前三真实自然样本在b62通过。`test_public_controlled_http`覆盖C01–C08/V01/V02；`test_scope_not_overridden_by_model_rewrite`覆盖模型省略日期门店仍按原问题过滤；2026-02历史制度在销售区间外可答，模型取证不依赖mock整体答案。 |
| 4 近主题错误与借数字 | 受控保护通过；真实缺失属性语义**未通过**。三类G2近主题（退款手续费、迟到申诉天数、花生克数）及非固定免费配送问法、身份证属性、无关编号与自由陈述都拒绝交付。真实chat4/5/6只有工程失败兜底，不能标此语义能力PASS。 |
| 5 注入与工具权限 | 受控通过。`test_retrieved_injection_retains_business_fact`真实检索含9999999/run_sql指令，仍回答合法31分钟；`test_injection_cannot_expand_tools`声明及入口拒run_sql/delete_sales，指标前后不变；原S01合法反馈事实仍可答。原凭证10项、工具/查数20项保持。 |
| 6 聊天引用展开 | 浏览器通过，使用受控HTTP模型+真实chat。1280/1440/390逐字对照实际响应、标题/生效日期/as_of/片段；`browser-final/`，未知字段兼容单独标为UI受控样本。UI未生成猜测元信息；390已目视检查。 |
| 7 独立材料替换、原RAG、trace与DEBUG_LOG | 通过。独立KB971在四格式31→47分钟重建重启，旧ID拒用；独立971/972历史版本与S01/S02适用性；固定b37的`fixed-rag.txt`199通过，最终轮数调整只改live常量。完整trace及DEBUG_LOG保留原因、过滤、证据、模型往返与失败。 |

## 可复现命令与实际结果

```bash
# 最终业务437aac1：38文档/轮数/绑定 + 10凭证 + 20查数/协议 + 53原后端
starter/.venv/bin/python -m pytest docs/verification/g3-02/test_document_binding.py docs/verification/g3-01/test_credentials.py docs/verification/g3-01/test_data_chat.py starter/tests -q
# six-round-backend.txt: 121 passed

G302_HTTP_OUT="$PWD/docs/verification/g3-02/http-six-rounds" starter/.venv/bin/python -m pytest docs/verification/g3-02/test_http.py -q
# http-six-rounds.txt: 26 passed。复跑请改用新的输出目录，勿覆盖已保存证据。

starter/.venv/bin/python -m pytest docs/verification/g3-02/test_budget_guard.py -q
# six-round-budget.txt: 6 passed，全离线/假上游

G2_EVIDENCE="$PWD/docs/verification/g3-02/fixed-rag-http" starter/.venv/bin/python -m pytest docs/verification/g2-01/test_ingestion.py docs/verification/g2-02/test_evidence.py docs/verification/g2-03/test_retrieval.py docs/verification/g2-04/test_doc_qa.py docs/verification/g2-04-heading-fix/test_heading.py -q
# fixed-rag.txt: b37业务固定字节199 passed；独立源码导出/重建/HTTP

python3 docs/verification/g3-02/verify_preservation.py
python3 docs/verification/g3-02/audit_live.py
```

`build.txt`前端typecheck/build成功。最终b37浏览器运行`g3-document.spec.ts`四项与看板20项，所有输出环境变量显式指向g3-02。`frontend-final.txt`为21PASS/3FAIL，三失败原因是workspace原测试明确要求mock，但第一次跑在受控live服务；没有改断言。随后`verify_frontend_mock.py`在真实no-Key服务重跑三个失败项，`frontend-mock.txt`3PASS。合计24个不同场景通过，保留错误模式的失败记录。前端业务从b62起未再改变；六轮调整只在后端live常量。

`verify_no_key.py`在b62独立源码/新var运行未经修改的55题公开评测：`no-key/report.json`为88.5/100、49/55，保持G2已知边界。它是修改后回归，不是修改前baseline，也不是真实模型全量评分。

初期`rag-final.txt`199PASS在开发过程中取得，另以固定b37业务字节完整重跑为`fixed-rag.txt`，以后一份作最终固定点证据。未运行最终全量真实55题、部署、混合、多轮语义或趋势引用。

## 真实模型与费用（不能以受控结果替代）

官方DeepSeek `deepseek-flash`，原始.env.live仅本地读取。定价重新抓取来源和时间见`pricing-source.json`，每次HTTP出站先预留2.20元，覆盖1,048,576输入×2元/百万+4096输出×8元/百万=2.12992元的保守上界。完整usage才结算释放；无usage/timeout保留预留；额度不足先拒发。六轮工具最多7模型回合，每回合至多2HTTP尝试，执行代理上限相应14，重试逐次预留；6项离线测试验证这些边界。运行脚本为特定授权执行器，不是产品计费平台。

| Chat | 固定点 | 实际结果 |
|---|---|---|
| 1 当前退款自然问法 | b62e6dc | 成功：KB013送达后24小时 |
| 2 2026-02-01历史储值 | b62e6dc | 成功：KB010充值500送50，销售区间外政策 |
| 3 Beef Poke过敏原 | b62e6dc | 成功：实际牛肉poke行+表头，麸质/大豆/芝麻 |
| 4 是否要求身份证 | b62e6dc | 未通过：重复检索后299868字节请求被本地尺寸保护拒发，HTTP400兜底 |
| 5 相同身份证问题 | b37af3d | 未通过：最大118762字节改善，仍超过4轮工具执行，tool_loop兜底 |
| 6 相同身份证问题，用户要求6轮 | 437aac1 | 未通过：最大119067字节，7次模型均HTTP200，第7次仍要工具，未执行第7轮，tool_loop兜底 |
| 7 相同身份证问题，最终阶段协议修复 | 777792a（产品=2dbd863） | 未通过：模型第4次主动refusal，但含v2/KB-013等说明，触发已有refusal数字校验，data_binding兜底；未进入none阶段 |

前三项是这些自然问法的真实证据，**不代表最终模型全面语义能力**。后四项均无错误事实交付，但未证明模型判断“资料未说明”。G3-05须继续列此负例；是否阻塞#25由主会话独立核验决定。

累计7chat、25实际出站API、另1本地拒发；输入524805、输出4965 token。高峰输入全部按未命中计算的保守估算1.089330元，非账单；无悬挂预留，本票未用6.910670元。与G3-01的0.047028合计第三关1.136358，剩余48.863642元，待协调会话核账。原4chat授权后，三次仅同问题追加均由主会话按用户授权从既有18定向池调配，总8元/第三关50元不变。原授权与5/6/7更新留在ledger。已停止真实调用，不再增加样本。

## 保护审计与失败留痕

原`protected-before.json`的2434项不完整：首次`git ls-files`未用`-z`，中文及反斜杠路径被Git引号转义后漏过prefix过滤。比前票3066少772个路径、另增加140项，不能说范围等价。保留该文件和初始错误说明；`verify_preservation.py`采用NUL安全ls-tree及hash-object：固定587ae82的3186个受保护tracked文件零差异，包含原data/KB/eval、G1/G2/G3-01全部提交证据。前票3066中3065项SHA256一致，1项草稿为用户确认自行删除/移动的外部例外（[#25评论](https://github.com/FHMinyi/moneki-ai-takehome/issues/25#issuecomment-5853212322)），不恢复。research两文件一致。`preservation-audit.json`保存发现时状态，`preservation-final.json`附授权例外，不把它改写为原3066全零差异。

新证据中的真实Key扫描0命中，未提交.env、共享venv/node_modules、索引缓存或运行var。原失败输出、样本与截图均保留；新增浏览器只写本票路径。初次测试误写未存在test_index.py、误选政策日期/别名/HTML标签、原S01攻击未在被检索片段中的断言、精简载荷测试不完整检索词、看板mock/live模式不匹配等均有原失败记录和DEBUG_LOG解释，不以绿灯覆盖失败。

资源和可重建临时目录详见`resources.json`。两个本票受控浏览器服务仍保留，等待主会话结束独立验证后明确清理。未新建worktree、未碰历史三worktrees、未合并/关Issue/部署/清理；原草稿用户例外之外，不改其他未提交材料。


## 最终阶段复审修正（2dbd863）

主会话检查chat6指出：第7次请求仍为auto且没有收尾提示，执行端虽拒绝第7轮工具，模型却不知道必须结束。这是当前票的协议缺口，不能将失败直接归因模型或转交G3-05。修正保持≤7模型回合、≤6轮工具和原时限，第7次实际HTTP请求tool_choice=none，告知只能按此前证据返回合法JSON或诚实说明当前依据不足；若违约仍给工具调用则在执行前记录异常并拒执行。不得机械把tool_loop改写成“资料不存在”。官方文档依据见tool-choice-source.json。

`finalization-backend.txt`121PASS；`finalization-retry.txt`1PASS（补充原生503→200重试两次请求均none）；`http-finalization.txt`30PASS；`http-finalization-negative.txt`4PASS/26 deselected，专门以原身份证问题验证受控最终refusal。合计最终后端122项、HTTP30个场景。这里的refusal由受控模型指定，只证明协议和失败保护，不能代替真实模型能力。主会话随后授权仅1次原问题复验，runner-only提交777792a（产品字节与2dbd863一致）执行chat7；旧chat4/5/6结果不变。当前结论为实现/免费验证完成，真实负例端到端尚未验收。


### 最后授权复验chat7（777792a，业务等同2dbd863）

实际4次模型调用均HTTP200，所有实际request的tool_choice为auto；模型在第4次较早结束，未进入第7次none阶段，不能称none已被真实模型验证。原始JSON为refusal，表示未找到外卖退款要求身份证的规定、无法确认，但附带v2/KB-013和对政策章节的解释，触发G3-01既有“refusal不得含数字/非法结构”的data_binding校验。最终用户仍收到工程失败提示，故端到端负例未通过；原始语义倾向改善与实际交付失败必须分开。

不为此放宽所有拒答数值、不追加词表、不修改题目或擅自再调用。该兼容性问题作为当前PR明确待审项；主会话决定后续修正与验收。完整raw/trace/usage保存chat7，无引用/无未经验证的事实交付。全部真实调用已停止。
