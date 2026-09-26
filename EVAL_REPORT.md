# 评测报告

更新日期：2026-09-27（北京时间）。

当前已完成原始 starter 的无 Key 基线、模型接入预检、真实模型基线，以及第一关数据看板修复与阶段验收。**最终版本全量评测尚未执行**。本报告中的 25.5/100 是原始 starter 接入真实模型后的分数，不能作为修复后的最终成绩。

## 1. 已完成的评测

| 记录 | 报告生成时间（北京时间） | 模型 / 模式 | 是否配置 Key | 公开题库得分 | 全通过题数 |
| --- | --- | --- | --- | --- | --- |
| 原始 starter 无模型基线 | 2026-09-26 23:31:38 | 本地降级模板 / `mock` | 否；启动时清除继承的模型配置 | **17/100** | **11/55** |
| 原始 starter 真实模型基线 | 2026-09-27 00:03:01 | DeepSeek `deepseek-flash` / `live` | 是；从本地 `.env.live` 读取，不记录 Key | **25.5/100** | **14/55** |
| 最终版本真实模型评测 | 尚未执行 | 待最终运行记录 | 待记录 | — | — |

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

**最终版本全量评测尚未执行；第 7 节仅给出第一关 metrics 类别的修复后结论。** 后续最终报告需新增独立记录，不覆盖这两组原始结果：

- 最终被测 commit、日期、准确运行命令、模型与关键配置、是否配置 Key。
- 完整公开题库原始输出、分类得分、失败项和耗时。
- 与原始真实模型基线的对比；若模型、数据、题库或配置发生变化，应明确说明可比性限制。
- 修复后的必要回归，以及实际做过的输入替换、新增文档和浏览器验收证据。

第一关已验证销售/门店/商品替换重建和浏览器体验（第 7 节）；尚未验证隐藏题库、知识库替换后的重建或真实服务的长期稳定性。真实模型基线只运行一次，不能据此证明输出稳定。记录的依赖版本支持复现环境，但未来重装仍受包源可用性影响。当前报告也不替代后续 `DEBUG_LOG.md` 的逐缺陷证据链或 `LLM_SETUP.md` 的最终接入说明。


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
