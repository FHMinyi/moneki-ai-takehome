# G3-02 第二轮审查修正及 G3-06 集成

最终业务固定点：`a868f10465cc8e6f1c48c41165612ef36a90a691`，是正常merge提交，父节点为本票修复`e1e07d5cda6b0eb04322b2d09e6aa09eeab08d90`和已验收main`118172e904728968136e6920701d0e8fb6dbb37c`。没有rebase或改写旧固定点。`fixed-source.json`保存业务源码哈希；随后证据提交只新增说明、输出和网络验证脚本，不改业务。

本轮全部为免费受控HTTP/浏览器/保存响应回放，没有新增模型阶段或付费。新binding语义解释仍由同次模型承担，代码只证明来源/锚点并检查有界角色冲突，不声称通用蕴含保证。

## 第二轮P1修正

固定0644f99审查发现：

- “外卖退款多久能到账”仍可用duration量型去对应24小时申请窗口；单字“内”还可冒充主体去引用储值30天。
- clarify的自由正文仍能传递无检索、无引用的政策断言。

红灯`f71c3b4`，九项全部失败，原主会话快照及原输出在`../review-roles/`。修复`e1e07d5`：主体不能是纯功能/数量/疑问成分，时长范围修饰不能冒充主体；属性不能单靠量型成立，focus之后的明确业务谓词必须有对应属性锚点；单位不是业务动作。复用原FOCUS_WORDS、_claim_terms与量型识别，没有到账/身份证/文档编号特判或新业务词表。原C08控制器迁移到实际迟到属性，value仍单独表示阈值；独立替换问题中的“提出”也有明确锚点，仍要求正例成功而非改成拒答。

clarify使用`missing_fields`枚举状态，由代码生成中性问题。兼容旧answer时仅抽取已知字段标签，整段政策正文不渲染；不是删除数字后继续显示。普通“请补充日期范围和门店”及数据回答保持可用，额外字段/未知字段被拒。真实工具错误仍是技术错误。

合并前183后端、57真实HTTP通过。新增星砂订单签收/复核、云帆工单归档/分派使用相同分钟量纲、不同业务动作，分别验证量型伪属性、非量型但遗漏后置动作、完整正确属性。所有负例均给完整schema和真实检索ID。

## 冲突与自动合并缺口

按照resolving-merge-conflicts技能读取了#28、PR32、原回执及交集代码。

- `ChatSidebar.tsx`冲突：同时保留本票Citation真实元信息和G306的TrendAttachment/引用生命周期。
- `live.py`冲突：中性refusal/clarify先处理；真正data回答仍在代码渲染前核对趋势有效metric。六轮工具+第七次none最终机会、重试/时间预算保持。
- `service.py`自动合并却有真实错误：趋势二参数lambda不接受文档引擎的`plan=`。`scoped-red.txt`及`red-http/`四项网络HTTP全红。修复受信任计划的关键字透传，search_kb继续按原Plan核对日期/门店，数据工具继续受趋势有效条件约束；未把plan开放为模型参数。`scoped-green.txt`四项通过，包含当前政策、明确历史日期+门店覆盖，以及refusal/clarify状态安全。
- 保留G306已修复的无context三参数引擎调用、宽泛前缀不误截断live路由、未知实体/越界停止、双窗口和显式商品约束；不是取一边覆盖另一边。

## 最终验证（明确隔离旧测试fixture）

**原`starter/tests/conftest.py`存在session级全局Retriever.search替换。原53项后端必须在独立Python进程运行，不要将它放在第三关/真实检索套件同一进程中。** 本票早先按starter/tests最后运行的组合213PASS保存为`backend.txt`，只是当时真实结果，不是稳健的复现方式。主会话发现改变顺序会污染后续检索后，本票以固定a868分进程补验：

| 检查 | 结果 | 输出 |
|---|---:|---|
| 文档/锚点/角色/六轮收束、完整凭证、查数、趋势路由与参数，不含旧53 fixture | 160 PASS | isolated-doc-trend.txt |
| 原后端，独立进程 | 53 PASS | isolated-original-backend.txt |
| 实际网络HTTP：原文档30+锚点19+新角色8+跨票4 | 61 PASS | http.txt / all-http |
| 独立网络条件矩阵 | 16 PASS | network-matrix.txt/json |
| 浏览器：原趋势7+引用卡与文档原文共存3 | 10 PASS | browser.txt / browser-trend / browser-doc |
| TypeScript/Vite | 成功 | build.txt |

网络矩阵包括普通无context误判绕过、原引用、文字覆盖、未知门店/商品、当前时点越界、全部时间、两个窗口比较、显式商品、未说明比较澄清、模型擅加/更换商品拒绝、模型篡改最终metric拒绝、全部门店覆盖、带引用查文档、带引用clarify不能转述政策。正确数据由独立只读SQLite核对net_revenue；业务结果没有被控制器替换。每条原请求、回答、trace、调用数完整保存。

浏览器1280/1440/390验证加入、删除/替换、筛选变化保持快照、发送后卡片保留、失败重试、新会话迟到响应隔离、普通无引用请求形状；新三项同时展开实际文档原文。390截图已目视核对引用卡、日期/门店范围、两条支持性引用均可读。受控模型不证明真实模型新的混合/多轮理解能力，本票也没有提前实现那些范围。

### 复现命令

从仓库根执行；使用新输出目录，避免覆盖任何历史证据：

```bash
G302_REPLAY_DIR=$(mktemp -d /tmp/g302-integration-check-XXXXXX)
G302_HTTP_OUT="$G302_REPLAY_DIR/http" G302_REVIEW_OUT="$G302_REPLAY_DIR/replay" \
starter/.venv/bin/python -m pytest \
  docs/verification/g3-02/review-roles/test_roles.py \
  docs/verification/g3-02/test_document_binding.py \
  docs/verification/g3-02/review-r1-r2/test_anchored_selection.py \
  docs/verification/g3-02/review-r1-r2/test_review.py \
  docs/verification/g3-06/test_early_plan_context.py \
  docs/verification/g3-06/test_route_regression.py \
  docs/verification/g3-06/test_trend_context.py \
  docs/verification/g3-06/test_live_budget.py \
  docs/verification/g3-01/test_credentials.py \
  docs/verification/g3-01/test_data_chat.py -q

# 单独启动另一个pytest进程，不能拼到上面的命令中。
starter/.venv/bin/python -m pytest starter/tests -q

G302_HTTP_OUT="$G302_REPLAY_DIR/network" starter/.venv/bin/python -m pytest \
  docs/verification/g3-02/test_http.py \
  docs/verification/g3-02/review-r1-r2/test_bound_http.py \
  docs/verification/g3-02/review-roles/test_roles_http.py \
  docs/verification/g3-02/integration-g306/test_cross.py -q
```

`controlled_server.py`为本票本地组合控制器，动态选端口、导出隔离源码并重建真实数据，`server-resources.json`记录a868服务。`verify_matrix.py`针对该记录执行矩阵。两个脚本均支持新的G302_INTEGRATION_OUT；矩阵可用G302_SERVER_RESOURCES指定对应资源文件，默认目标已存在会在执行前拒绝覆盖。模型仅产生工具调用/选择，真实数据在业务服务查询；场景通过本地`/case`设置，不是通用真实模型。

本次浏览器实际命令（frontend目录；复跑应换全新的各输出目录）：

```bash
BROWSER_BASE_URL=http://127.0.0.1:59458 \
G306_MODEL_URL=http://127.0.0.1:59457 \
G306_EVIDENCE_DIR=../docs/verification/g3-02/integration-g306/browser-trend \
G302_INTEGRATION_OUT=../docs/verification/g3-02/integration-g306/browser-doc \
npx playwright test tests/g3-trend-context.spec.ts tests/g3-integrated-document.spec.ts \
  --workers=1 --output=../docs/verification/g3-02/integration-g306/browser-runtime-results
```

## 保护、费用和资源

`protected-main.json`固定incoming main118172e的3251个原输入/KB/评分器/基线/历史证据Git blob，含G306全部65个文件。`preservation.json`为零差异；G302旧chat1—7及账本与0644f99一致。未覆盖G306或G301原失败、截图、脚本。原用户移除草稿例外及research保护沿用前述审计；未恢复草稿。

本票仍7chat/25实际API、峰时全未命中估算1.089330元（非账单），本轮新增真实调用为零。G306的0.030810元是其独立账本，不算本票新增；第三关总账仍由主协调会话汇总。新合并协议和语义能力没有新增真实模型复验，免费回放不能冒称实时模型结果。

`resources.json`列出最新harness58730/model59457/API58732:59458，及三组仍保留的历史受控服务。所有临时根、共享环境、需保留证据和可重建运行产物均列出。尚未停止服务、删除任务分支、合并PR或清理；主会话独立核验与合并后等待具体指令。G306独立工作树仍由主会话管理，未接管。

原始pytest红灯日志含其自带空白，保持原样，不为让diff空白检查通过而改写；业务代码/前端diff检查通过。
