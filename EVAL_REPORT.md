# 评测报告

更新日期：2026-09-27（北京时间）。

第二关固定点 `b5c756e` 的无 Key 全量结果为 **88.5/100、49/55**。第三关首个集成固定点 `4591fab` 已从源码新安装并完成官方原 55 题：无 Key **94/100、53/55**，DeepSeek `deepseek-flash` **67.5/100、40/55**。真实结果暴露文档、版本、混合及多轮缺陷，属于修复前的第三关集成检查点；后续新固定点完整复验须单列，不覆盖本轮。原 starter live **25.5/100** 属于另一历史代码阶段。第 8 节保留第二关结果；本轮见第 10 节。

## 1. 已完成的评测

| 记录 | 报告生成时间（北京时间） | 模型 / 模式 | 是否配置 Key | 公开题库得分 | 全通过题数 |
| --- | --- | --- | --- | --- | --- |
| 原始 starter 无模型基线 | 2026-09-26 23:31:38 | 本地降级模板 / `mock` | 否；启动时清除继承的模型配置 | **17/100** | **11/55** |
| 原始 starter 真实模型基线 | 2026-09-27 00:03:01 | DeepSeek `deepseek-flash` / `live` | 是；从本地 `.env.live` 读取，不记录 Key | **25.5/100** | **14/55** |
| 第二关启动诊断 | 2026-09-27，见诊断报告 | 本地降级 / `mock` | 否 | **41/100** | **25/55** |
| 第二关整体验收 | 2026-09-27 14:07:36 | 本地原文抽取 / `mock` | 否；三个LLM变量移除 | **88.5/100** | **49/55** |
| 第三关首个集成检查点 `4591fab` | 2026-09-27，原报告记录精确时间 | 当前降级路径 / `mock` | 否 | **94/100** | **53/55** |
| 第三关首个集成检查点 `4591fab` | 2026-09-27，原报告记录精确时间 | DeepSeek `deepseek-flash` / `live` | 是；凭证不入库 | **67.5/100** | **40/55** |
| 本次失败修正后新固定点的完整复验 | 待实际执行 | 待统一集成提交 | 待记录 | — | — |

两次基线均使用完整的 `eval/public_questions.jsonl`，共 55 题，评测请求超时为默认 180 秒，未按类别筛选。上述 100 分是公开题库评测器的分值，不等同于任务书的作业与现场面试综合评分。

### 代码固定点与证据提交

| 记录 | 运行时仓库 HEAD | 证据保存提交 |
| --- | --- | --- |
| 无模型基线 | `f32daa70b8236429a0daad2090c6e91dc309deb6` | `b5703aa` |
| 接入预检与真实模型基线 | `b5703aa596670674ec811a028de9bd5167139564` | `2e79227` |

真实模型运行时的 HEAD 比无模型运行时多了证据文档；两个提交之间的 `starter/`、`eval/`、`data/`、`knowledge_base/` 无差异。因此，两组初始结果对应的**业务代码固定点均为 `f32daa70b8236429a0daad2090c6e91dc309deb6`**。证据保存提交是运行之后的材料归档，不是被测业务代码的新版本。

原始结果与运行说明：

- 无模型：[运行说明](docs/baseline/2026-09-26T233022-f32daa7-mock/BASELINE.md)、[原始报告 Markdown](docs/baseline/2026-09-26T233022-f32daa7-mock/report.md)、[原始报告 JSON](docs/baseline/2026-09-26T233022-f32daa7-mock/report.json)、[失败题清单](docs/baseline/2026-09-26T233022-f32daa7-mock/failed-questions.tsv)。
- 真实模型：[运行说明](docs/baseline/2026-09-26T235144-f32daa7-live/LIVE_BASELINE.md)、[原始报告 Markdown](docs/baseline/2026-09-26T235144-f32daa7-live/report.md)、[原始报告 JSON](docs/baseline/2026-09-26T235144-f32daa7-live/report.json)、[失败题清单](docs/baseline/2026-09-26T235144-f32daa7-live/failed-questions.tsv)。

## 2. 运行环境、配置与命令

### 共同条件

- Python **3.12.14**。真实模型阶段复用无模型阶段的虚拟环境；完整依赖版本见 [依赖清单](docs/baseline/2026-09-26T233022-f32daa7-mock/dependencies.txt)。
- 原始 starter 被复制到系统临时目录后重建与运行，清洗库和检索缓存写入副本；原 checkout 的业务代码与输入不变。
- `DATA_DIR`、`KB_DIR` 指向仓库原始输入，`VAR_DIR` 指向临时运行目录；系统“今天”使用默认 **2026-09-01**。
- 两轮均保存了输入前后 SHA-256 清单，比较结果一致。详见两轮运行说明及同目录的 `input-sha256-before.txt`、`input-sha256-after.txt`。
- 本轮只保存原始结果，没有为提高得分修代码、改题库或重复运行真实模型整套评测。

### 无模型基线

服务通过 `env -i` 启动，未注入 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`，健康接口确认 `llm_mode=mock`。以下为本次评测命令，从仓库根目录执行；环境准备、隔离副本重建和服务启动命令见[无模型运行说明](docs/baseline/2026-09-26T233022-f32daa7-mock/BASELINE.md)。

```bash
env -i PATH='/opt/homebrew/bin:/usr/bin:/bin' HOME="$HOME" \
  /opt/homebrew/bin/python3.12 eval/run_eval.py \
  --base-url http://127.0.0.1:53176 \
  --questions eval/public_questions.jsonl \
  --out docs/baseline/2026-09-26T233022-f32daa7-mock
```

### 真实模型基线

- 上游：`api.deepseek.com`；模型：`deepseek-flash`；协议：OpenAI 兼容 Chat Completions。
- `.env.live` 按数据格式读取，未作为 shell 脚本执行；服务子进程通过环境变量接收配置。该文件被 Git 忽略，不属于交付证据。
- 真实请求经过仓库自带 `llm_gateway.py` 的本地代理。代理没有注入或改写模型参数，日志不保存真实授权头值。
- 评测代理日志中，119 次请求均使用 `max_tokens=4096`、`tool_choice=auto`；未显式发送 `temperature`、`thinking`、`stream` 或 `response_format`。参数未发送不代表服务端关闭了对应能力。
- 本地服务的 `LLM_BASE_URL` 指向代理提供的带 `/ds-gw` 前缀的地址；代理转发到上述真实上游。模型配置摘要见[脱敏配置记录](docs/baseline/2026-09-26T235144-f32daa7-live/model-config-sanitized.json)。

以下为本次完整评测命令；安全加载配置、代理与服务启动方式见[真实模型运行说明](docs/baseline/2026-09-26T235144-f32daa7-live/LIVE_BASELINE.md)。评测器命令本身不加载 Key，Key 已由被测服务的进程环境提供。

```bash
env -i PATH='/opt/homebrew/bin:/usr/bin:/bin' HOME="$HOME" \
  python3.12 eval/run_eval.py \
  --base-url http://127.0.0.1:60040 \
  --questions eval/public_questions.jsonl \
  --out docs/baseline/2026-09-26T235144-f32daa7-live
```

以上命令记录历史运行条件，本轮服务均已停止。复现时需要先按运行说明重建并启动服务，换用实际监听端口，且将 `--out` 改为新的独立目录，避免覆盖原始证据。真实阶段会再次调用供应商并产生费用。

## 3. 公开题库分类结果与对比

下表直接汇总两份原始报告，分子和分母分别是得分与该类别满分，不是通过题数。

| 类别 | 无模型基线 | 真实模型基线 | 得分变化 |
| --- | ---: | ---: | ---: |
| 指标接口 `metrics` | 1/6 | 1/6 | 0 |
| 检索质量 `retrieval` | 6/15 | 6/15 | 0 |
| 纯数据问答 `data` | 0/12 | 0/12 | 0 |
| 纯文档问答 `doc` | 0/16 | 2/16 | +2 |
| 版本与时效 `version` | 0/6 | 0/6 | 0 |
| 混合问答 `hybrid` | 0/18 | 0/18 | 0 |
| 多轮追问 `multi_turn` | 1/9 | 2.5/9 | +1.5 |
| 拒答 `refusal` | 6/8 | 8/8 | +2 |
| 安全 `safety` | 3/9 | 6/9 | +3 |
| 健康检查 `health` | 0/1 | 0/1 | 0 |
| **合计** | **17/100** | **25.5/100** | **+8.5** |

无模型阶段 44 题未全通过；真实模型阶段 41 题未全通过。逐题得分提升仅发生在 C02（+2）、T03（+1.5）、F01（+2）、S02（+3），其余 51 题得分不变，没有降分题。多轮题可能仅部分轮次通过，因此“得分提高”和“整题全通过”不能混为一谈。[机器可读对比](docs/baseline/2026-09-26T235144-f32daa7-live/mock-vs-live.json)

这 **+8.5 分是同一原始代码切换问答模式后的单次观察，不是代码修复收益**。指标与检索分数完全未变，纯数据与混合问答仍为 0 分；真实接入成功不足以证明经营答案可信。具体单题根因需在后续修复中通过复现、失败测试和回归验证，不能仅由分类分数推断。

真实模型完整公开评测的请求耗时：中位数 **1.987 秒**，最大 **38.011 秒**，累计 **231.862 秒**。这是报告中的评测请求耗时统计，不含环境准备、预检与冒烟，也不是生产性能承诺。

## 4. 接入预检及辅助验证

### 本地接入预检

使用原始代码对本地假上游执行 `eval/llm_gateway.py preflight`，不使用真实 Key、不调用收费模型。覆盖默认 16 个场景与两道中性问题，包含多工具调用、错误码、空输出、保持连接及长时间无响应等情形。

命令结构如下；端口和输出目录由该次隔离运行分配，不能直接沿用示例占位符：

```text
python3.12 eval/llm_gateway.py preflight \
  --service-url http://127.0.0.1:<预检服务端口> \
  --port <假模型端口> --no-wait \
  --out <新建的独立报告目录>
```

结果为 **P1–P14 全部 PASS，0 FAIL、0 SKIP，退出码 0**。32 次本地问答均返回 HTTP 200；假上游观察到 60 次 POST 和 44 个工具调用结果；最慢一次约 120.02 秒，低于 180 秒预算。预检使用工具提供的假 Key 和假模型名，不计入上面的真实模型用量。

证据：[预检报告 Markdown](docs/baseline/2026-09-26T235144-f32daa7-live/preflight_report.md)、[预检报告 JSON](docs/baseline/2026-09-26T235144-f32daa7-live/preflight_report.json)、[原始输出](docs/baseline/2026-09-26T235144-f32daa7-live/preflight.output.txt)。预检证明此次协议场景的处理结果，不替代业务题正确性评测。

### 已有测试与真实接入冒烟

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 无模型阶段原始重建 | 退出码 0；18,628 行全部保留，索引 25 篇 / 53 片段 | [重建输出](docs/baseline/2026-09-26T233022-f32daa7-mock/rebuild.output.txt) |
| starter 自带测试 | 17 passed，1 个弃用警告 | [测试输出](docs/baseline/2026-09-26T233022-f32daa7-mock/starter-tests.output.txt) |
| 评测器自身测试 | 260 tests，OK | [评测器测试输出](docs/baseline/2026-09-26T233022-f32daa7-mock/evaluator-tests.output.txt) |
| 真实接入冒烟 | 4 次本地问答，产生 14 次真实上游请求；均 HTTP 200 且有 usage | [冒烟调用摘要](docs/baseline/2026-09-26T235144-f32daa7-live/smoke-proxy-summary.json) |

上述重建结果是原始行为记录，不表示清洗和索引正确。starter 测试夹具替换了真实检索，因此测试全绿不能证明知识库检索有效；260 项测试验证的是评测工具本身。

冒烟中，纯数据题返回 `data` 和数据证据；文档题返回 `refusal`；混合题返回 `doc` 且无数据证据；追问返回 `clarify`。这说明 HTTP 成功和模型接入成功不能等同于用户任务完成，详见[真实模型运行说明](docs/baseline/2026-09-26T235144-f32daa7-live/LIVE_BASELINE.md)。

## 5. 真实调用用量

以下统计来自供应商响应中的 `usage`，不含本地预检。

| 范围 | 上游请求数 | 输入 tokens | 输出 tokens | 合计 tokens |
| --- | ---: | ---: | ---: | ---: |
| 冒烟 | 14 | 70,993 | 6,108 | 77,101 |
| 一次完整公开评测 | 119 | 749,463 | 42,061 | 791,524 |
| **合计** | **133** | **820,456** | **48,169** | **868,625** |

133 次请求均 HTTP 200，均有 usage 记录。输入缓存命中合计 569,856 tokens，响应另报告 reasoning tokens 合计 29,687；这些是明细统计，不应再次叠加到 total tokens 上。未核实供应商账单或计费价格，**实际费用未知**。

证据：[评测调用摘要](docs/baseline/2026-09-26T235144-f32daa7-live/eval-proxy-summary.json)、[冒烟调用摘要](docs/baseline/2026-09-26T235144-f32daa7-live/smoke-proxy-summary.json)。同目录保留两份 `*-proxy-sanitized.jsonl` 脱敏调用记录；基线材料的真实 Key 字节匹配检查为零命中。

## 6. 最终评测待补与当前限制

**本节原为第一关后的待办；当前无 Key 全量评测和KB替换已完成，见第8节。修复后真实模型评测仍待后续授权执行。** 真实模型报告需新增独立记录，不覆盖原始结果：

- 最终被测 commit、日期、准确运行命令、模型与关键配置、是否配置 Key。
- 完整公开题库原始输出、分类得分、失败项和耗时。
- 与原始真实模型基线的对比；若模型、数据、题库或配置发生变化，应明确说明可比性限制。
- 修复后的必要回归，以及实际做过的输入替换、新增文档和浏览器验收证据。

第一关已验证销售/门店/商品替换重建和浏览器体验（第7节），第二关新环境复验及KB替换见第8节；尚未验证隐藏题库或真实服务的长期稳定性。真实模型基线只运行一次，不能据此证明输出稳定。记录的依赖版本支持复现环境，但未来重装仍受包源可用性影响。当前报告也不替代后续 `DEBUG_LOG.md` 的逐缺陷证据链或 `LLM_SETUP.md` 的最终接入说明。


## 7. 第一关阶段评测（G1-05，2026-09-27）

被测应用源码：`6d42e85a2d4e52cb1841e51cd67d855ab519dde2`，包含 #10 精修页面。来源固定点 `839ec49`。
运行前从该提交导出全新源码副本，无已有 venv、node_modules、dist、clean.db、index cache 或 `.env.live`，按根 README 三步安装/构建/启动。
环境为 macOS 26.7 arm64、Python 3.12.14、Node 24.19.0、npm 12.0.2；[完整记录](docs/verification/g1-05/README.md)。
模型配置：没有 Key，三个 LLM 变量明确清除，`llm_mode=mock`；无需模型名、base URL、温度或 token 配置，本轮无模型请求。

从该源码副本根目录执行：

```bash
python3.12 eval/run_eval.py --base-url http://127.0.0.1:8015 \
  --questions eval/public_questions.jsonl --only metrics \
  --out /tmp/moneki-g1-05-4r7gvnd1/metrics
```

| 类别 | 原始两组基线 | 第一关修复后 | 边界 |
| --- | --- | --- | --- |
| metrics（M01–M06） | 均 1/6 | **6/6，6 题全通过** | 本关六分制，不是最终全量 100 分 |
| 全量题库 | mock 17/100；live 25.5/100 | 未重跑 | 不把局部 100% 当全量成绩 |

证据：[逐题输出](docs/verification/g1-05/metrics.txt)、[原始 JSON](docs/verification/g1-05/metrics/report.json)、[Markdown](docs/verification/g1-05/metrics/report.md)。
题库和原始输入未改变。两组原始基线及前序证据保持原样；[187 文件保护核验](docs/verification/g1-05/preservation.json)。

补充门槛：53 项后端通过；类型检查及生产 build 通过；原始浏览器 26 项、独立替换数据 3 项、全空销售 3 项均通过。
健康清洗结果 18,628→18,290（剔除 338），实际范围 2026-05-01～2026-08-31。
替换手算净额 52.02、2 单、客单价 26.01；质量台账/门店/三块结果/真实浏览器一致。
这些验证覆盖指标题以外的边界，不能替代第二至四关评测。

已知限制：`kb_docs=36` 仍按文件计数，N01 整题未作为本关通过项；知识库缓存键与检索缺陷未修复。
预生成索引从 Git 取消跟踪后，干净重建生成 72 chunks（旧基线缓存 53），仅记录实际差异，不宣称 RAG 修复。


## 8. 第二关整体验收（G2-05，新环境，2026-09-27）

实际被测完整提交 **`b5c756e04302b14583b50ca83d07eee106285efa`**：将已审查的PR22/main `4634dff`正常合并到G2-05分支，业务字节与该main相同。报告之后的提交只保存脚本、证据和说明。源码为git archive导出，新建venv、npm ci后实际执行根README三步。运行环境macOS26.7 arm64、Python3.12.14、Node24.19.0；[新环境记录](docs/verification/g2-05/final/README.md)。

以下分数属于不同历史阶段，不能将代码变化与模式变化混为同一收益：

| 类别 | 原始mock | 原始live | G2起点mock | 当前G2 mock |
|---|---:|---:|---:|---:|
| metrics | 1/6 | 1/6 | 6/6 | 6/6 |
| retrieval | 6/15 | 6/15 | 7/15 | 15/15 |
| data | 0/12 | 0/12 | 12/12 | 12/12 |
| doc | 0/16 | 2/16 | 0/16 | 16/16 |
| version | 0/6 | 0/6 | 0/6 | 5/6 |
| hybrid | 0/18 | 0/18 | 3/18 | 12/18 |
| multi_turn | 1/9 | 2.5/9 | 2/9 | 4.5/9 |
| refusal | 6/8 | 8/8 | 8/8 | 8/8 |
| safety | 3/9 | 6/9 | 3/9 | 9/9 |
| health | 0/1 | 0/1 | 0/1 | 1/1 |
| 总分/全绿 | 17/100，11/55 | 25.5/100，14/55 | 41/100，25/55 | **88.5/100，49/55** |

原始两组业务基点f32daa7，命令与配置见第2节；G2起点为094ae6d，[诊断原始报告与命令](docs/diagnostics/2026-09-27-g2-start/README.md)。当前[原始JSON](docs/verification/g2-05/final/integration/eval/report.json)和[Markdown](docs/verification/g2-05/final/integration/eval/report.md)使用未改55题、未改评分器，无类别筛选。

当前准确评测命令（cwd为新导出源码根目录）：

```bash
/private/tmp/moneki-g1-05-6yeq26mj/source/starter/.venv/bin/python eval/run_eval.py \
  --base-url http://127.0.0.1:60112 --questions eval/public_questions.jsonl \
  --out /tmp/moneki-g205-final-rag/eval
```

服务由同目录`make run PORT=60112`启动；先`make setup`/`make rebuild`，全部准确命令及cwd见final/clean-delivery/commands.json与final/integration/commands.json。移除LLM_API_KEY/LLM_BASE_URL/LLM_MODEL和外部DATA_DIR/KB_DIR/VAR_DIR/TODAY/PYTHONPATH；没有Key，未加载.env.live，无模型名、温度或token参数，today固定2026-09-01。依赖只使用下载缓存加速，全新安装环境；实际35篇215块、18290条清洗明细。生成时间原始报告为UTC 06:07:36，对应北京时间14:07:36。

仍未全绿：**V03、H01、H06、T01、T02、T03**。V03首轮通过、追问第二轮失败；T01首轮通过后两轮失败，T02前两轮通过第三轮失败，T03首轮通过第二轮失败。独立完整历史问句不能替代这些多轮题。与G2-04 R1逐题逐轮比较无已通过回归；具体失败检查保存在原报告及final/integration/vs-r1.json。安全公开9/9不表示完整安全对抗已验收。

旧G2-05 checkpoint在358859a同为88.5分，却由独立KB夹具发现无标题正文被误当标题的第二关阻塞。该旧失败、输入和A/B永久保留于docs/verification/g2-05；经G2-04/PR22修复后，本轮重新安装、新源码重跑原脚本，5阶段7问与4问A/B均通过，不能仅凭同分断言问题不存在。

这是当前第二关的**无模型结果**。混合、多轮、会话、聊天UI及修复后真实模型验收仍待后续，不把有限mock规则扩张成任意自然语言可回答的承诺。

## 9. G3-01 查数闭环（2026-09-27）

本票原始55题无Key回归仍为88.5/100、49/55，未改变评分器；最终业务固定1608043，输出见docs/verification/g3-01/no-key-final。该结果是修改后回归，不是第三关前置重跑基线：修改前只在2839c67业务字节上执行本票新增红灯探针9F/1P。

真实模型只做三次单轮chat，不是全量评测：f991720首次正确查数但错误引用工具名，按规则refusal；354f6d4显式回传call_id后两条同范围样本成功（六月417份、七月净额13635相对六月15889减少2254、-14.19%），独立SQL核对见docs/verification/g3-01/live/audit.json。供应商DeepSeek官方、deepseek-flash、默认思考、max_tokens4096，真实Key经执行代理安全使用。共6次API（含失败），18,834输入token与1,170输出token；按高峰输入全部未命中估算0.047028元，未核对账单。最终1608043增加无数据澄清JSON结构，未追加付费语义测试。

**以上是 G3-01 当时的阶段结论**：彼时没有完整真实模型 55 题分数，两条成功样本不能换算成准确率。后续 G3-05 已跑一次完整真实评测，结果和缺陷见第 10 节；两个时间点不得混写。

## 10. 第三关首个集成整体验收检查点（G3-05）

以下记录是 **`4591fab9a80ef63c440b9a117dbbc4fcbf03c430`** 业务源码。它包含 G3-01/02/03/04/06 的已合并版本，但真实全题揭示仍需修复；保存原失败作为新的固定对照，不当最终通过结论。G3-01 启动时只有定向红灯，没有“修复前完整第三关 fresh 55 题”可供比较，不会事后补造。

从 `git archive` 导出不含环境和缓存的源码，新建 Python 3.12 venv 实际 `pip install -r starter/requirements.txt`，`npm ci`、Vite 构建和后端重建。第二份相同提交的独立导出保留 pip/npm/build/rebuild 全部日志，输入 SHA-256 一致。平台、精确命令、健康快照、原始脚本、环境边界和文件清单见 [G3-05 检查点](docs/verification/g3-05/README.md)。官方原 `eval/run_eval.py` 和 `public_questions.jsonl` 均未修改，逐题串行完整 55 题、保留多轮原顺序；无 Key 与 live 两轮输出分别写到新目录。

| 分类 | 4591fab mock | 4591fab live |
| --- | ---: | ---: |
| 指标 | 6/6 | 6/6 |
| 检索 | 15/15 | 15/15 |
| 纯数据 | 12/12 | 12/12 |
| 纯文档 | 16/16 | **0/16** |
| 版本与时效 | 6/6 | **0/6** |
| 混合 | 12/18 | 15/18 |
| 多轮 | 9/9 | 4.5/9 |
| 拒答 | 8/8 | 8/8 |
| 安全 | 9/9 | 6/9 |
| 健康 | 1/1 | 1/1 |
| **总分 / 整题通过** | **94/100 · 53/55** | **67.5/100 · 40/55** |

无 Key 两题未全通过：**H01、H06**。真实模型 15 道未全通过：**C01–C08、V01–V03、H04、T02、T03、S01**；V03、T02、T03 逐轮失败不能压缩为一个总分。H01/H02/H03/H05/H06、T01 在本轮真实运行通过，亦不能用这些通过项抵销文档与多轮缺口。所有原始 checks、请求/响应、trace、模型往返、费用和 18 个失败 turn 的原因分类见 [live 原始报告](docs/verification/g3-05/eval-live/report.json)、[逐轮记录](docs/verification/g3-05/eval-live/chat-trace.jsonl)、[失败索引](docs/verification/g3-05/eval-live/failure-summary.json)，无 Key 原始报告在 [mock 目录](docs/verification/g3-05/eval-mock/report.json)。

真实失败原因不合并：10 轮文档主体/属性绑定冲突，3 轮思考耗尽 4096 输出额度，4 轮混合来源/日期/范围关系核验失败，1 轮因前轮拒答后无可继承上下文而澄清。拒绝错误的来源或范围是必要的，但它没有使运营问题完成。用户随后明确把资料片段之间的自然语义选择交给同一次模型解释，确定性 ID、原文位置、来源范围、实际查询、数值计算和工具权限仍须程序核验；这个后续设计决定不改变旧 4591fab 的原始失败。修复与新固定点复验另存新目录。

本轮 87 次上游 API 都是 HTTP 200 且 usage 完整，输入 **812,593 tokens**、输出 **49,144 tokens**。按峰值输入全未命中缓存 **2 元/百万**、输出 **8 元/百万**计算，估算 **2.018338 元**；加此前第三关 **1.440556 元**，累计 **3.458894 元**、50 元授权内余 **46.541106 元**，没有悬挂预留。每一次请求（含重试）先保留 2.20 元，收到完整 usage 才结算；这不是供应商账单，没做余额或模型列表探测。请求与账本见 [原始模型流量](docs/verification/g3-05/eval-live/model-traffic.jsonl)和 [费用账本](docs/verification/g3-05/eval-live/ledger.json)。

官方免费接入预检为 **P1–P13 PASS、P14 SKIP**，不能写成全通过；独立 typed 受控上游证明非流式正常/延迟 HTTP 和超时返回，但不替官方 SSE 项打分。真实模型完整复验上限为修复集成后**最多一次**；此检查点不是选择性重跑后留下的“最好一次”。
