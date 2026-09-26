# G2-04：单轮文档问答执行证据

## 当前交付：主会话审查修正 R1

主会话对初次交付 `f2d2fff` 独立复核后发现近主题自然问法仍误答，第5/6项当时未满足。以下R1结果取代初次自验结论；下方初次交付记录和原88.5分报告保留作历史，不冒充这次复核证据。

- 原执行固定点：`174cc635b7ae547b939bcbfb03091af7e3b59916`；R1审查固定点：`f2d2fff4b8a2f06db8bb405416588f9be7218c8a`。
- R1最终被测业务提交：**`c7130778c6c04ad6fe1dce6b6d7610f196333236`**。后续提交只整理证据/文档。
- **82项本项、97项前序、53项原后端通过**；完整未改题库无Key **88.5/100、49/55全绿**。
- 对G2-03：36保持、13新增、原通过轮次无回归；对初次88.5分交付：49个全绿保持、原通过轮次无回归。
- 仍未全绿V03/H01/H06/T01/T02/T03，不把V03首轮或其他部分轮次通过写成多轮完成。
- 修复和本地验证完成，**等待主会话再次独立核验**；不宣告合并或Issue关闭。

### R1复现命令

```bash
G2_EVIDENCE=/tmp/g2-04-r1-review-http starter/.venv/bin/python -m pytest docs/verification/g2-04/test_doc_qa.py -q
G2_EVIDENCE=/tmp/g2-04-r1-review-predecessors starter/.venv/bin/python -m pytest docs/verification/g2-01/test_ingestion.py docs/verification/g2-02/test_evidence.py docs/verification/g2-03/test_retrieval.py -q
starter/.venv/bin/python docs/diagnostics/2026-09-27-g2-start/baseline.py --repo "$PWD" --out /tmp/g2-04-r1-review-integration
starter/.venv/bin/python docs/verification/g2-04/audit.py /tmp/g2-04-r1-review-http /tmp/g2-04-r1-review-answers.json
starter/.venv/bin/python docs/verification/g2-04/compare.py docs/verification/g2-03/integration/eval/report.json /tmp/g2-04-r1-review-integration/eval/report.json /tmp/g2-04-r1-vs-g203.json
starter/.venv/bin/python docs/verification/g2-04/compare.py docs/verification/g2-04/integration-restored/eval/report.json /tmp/g2-04-r1-review-integration/eval/report.json /tmp/g2-04-r1-vs-original.json
```

输出目录用新名字。baseline导出调用时HEAD，复用已有venv；源码、缓存、VAR_DIR隔离，显式移除LLM变量，不加载.env.live、不调用模型。异常诊断的两项故障注入与真实RAG验收分开。

### R1八项验收

| # | 检查 | 最新实际证据 |
|---|---|---|
| 1 公开文档/单轮版本 | C01—C08、V01/V02及契约检查全通过 | `review-r1-integration/eval/report.md/json`，无Key真实HTTP，未改题库评分器 |
| 2 正确路由 | 11项原文档路由保持，H05既有数据+原因路径保持 | `review-r1-acceptance.txt`和对应HTTP；plan/doc无错误经营查询 |
| 3 明确历史日期 | 原5项历史/版本边界与全角日期保持 | 同套82项；V03追问原题第二轮仍失败，未扩大多轮 |
| 4 引文来源 | 每次build核对实际正分非补位块/表头中的连续原文；HTML/GBK/表格/尾段、规范化400字边界保持 | `review-r1-final-answer-audit.json`：90问答/90trace、61doc、身份错位0；`review-r1-source-audit.json`：35篇215块遗漏0、15问75条错位0 |
| 5 缺事实不编造 | 原缺属性/单位、文档指令检查保持；新增普通吗问句、正反问、否定、省略和跨主体反例 | `review-r1-parent-recheck.json`主会话四问全部refusal无引文；原三个误答分别不再回答退款审批/生日赠饮/目标销量 |
| 6 改写和输入替换 | 新增的普通问法使用同一claim抽取/证据约束；有依据的审批/叠加/提现/芝麻正常答；权限归属重建后互换 | `test_natural_*`、`test_elliptical_*`、`test_boolean_subject_and_replacement`、`test_boolean_subject_cannot_cross_clauses`；不存在题号、docID、身份证/花生/积分属性列表或固定答案补丁 |
| 7 可诊断 | evidence.required_claim记录问题主体、属性、词项、实体；候选被拒用时保留该约束；异常trace与HTTP契约保持 | `review-r1-acceptance-http/`及`review-r1-test_error_trace[...]-server.log.txt`；90条trace可取回 |
| 8 保持前序 | 82本项/97前序/53原后端；metrics/data/retrieval/refusal全过，S02/S03和两库hash门禁保持 | `review-r1-final-predecessors.txt`、`review-r1-integration/backend-tests.txt`；`review-r1-vs-g203.md/json`及`review-r1-vs-original.md/json`逐题逐轮无回归 |

### R1实际修复与红绿

前一实现仅识别部分布尔前缀；没有识别到就按普通文档主题取句。新路径先区分开放疑问与闭合命题，识别主体和所问属性；同一候选分句必须同时支持主体与属性，已识别实体要一致。不能因为另一主体有同一属性，或同一句中另一分句提到该属性，就转移事实。表格通过同一行的实体和同源表头解释属性，保留原连续引用映射。

- `33a6427`：17项8失败9通过，另同分句/分号主体反例1失败；`3e53810`修复后69项通过。
- `review-r1-attempt.txt`保留初修4失败20通过：过度删除主体尾部“申请”误伤真实退款审批，恢复主体文本后通过，未降低断言。
- `8297bb1`：省略/否定11项10失败1通过，其中3项正常对照要求trace确实进入claim校验；`705bdc4`修复后80项通过。
- 首轮完整评测86.5分暴露“什么”的末字么误判。`b8689a7`提交V03首轮/T02第二轮两项真实红灯和`review-r1-before-wh-integration/`；`c713077`开放疑问优先，31项对照通过，最终82项/88.5分。
- 最终评测见`review-r1-integration/`；原`integration-restored/`88.5分与本轮86.5分均保留，不覆盖旧输出。

这仍是保守的无模型结构/词项校验，不是通用语义蕴含证明。完整句法、任意同义表达或跨句推理可能拒答；没有声称隐藏题或所有布尔问句都正确。关键变化是不能只凭主题或孤立属性词选择邻近事实；对普通有依据的问题仍返回原文，而不是一律拒绝布尔问题。未改变混合编排、会话、前端或live路径。

### R1资源和保护

`review-r1-preservation.json`：905个原保护文件变化0。既有未跟踪草稿和research仍保留；共享分支`codex/g2-04-doc-qa`，未动其他checkout。`review-r1-resources.json`记录本轮519次自建服务，全部finally退出；前一轮715次记录仍在原resources.json。最终集成PID61358/端口54267已停止，无常驻自建服务。保留仓库证据和`/tmp/moneki-g2-04-review-r1-*-integration`；部分较早pytest临时目录会由框架自动回收。未主动清理分支/共享目录或其他进程，不合并不关闭Issue。

## 初次交付记录（保留作历史，已由上方R1结果取代）

规格 [Issue #16](https://github.com/FHMinyi/moneki-ai-takehome/issues/16)。执行固定点 **`174cc635b7ae547b939bcbfb03091af7e3b59916`**（已核对当时本地main及远端）；最终被测业务提交 **`67b0f6255c2e1c2de1bd6e13c14a8a72c9ee5b3d`**。后续提交只整理测试、证据和说明。执行模型 GPT-6 Astra/high；未派生子agent。实施和本地验证完成，等待主会话独立验收；本文件不宣告Issue已关闭。

最终无模型 **88.5/100，49/55整题全绿**；C01—C08与V01/V02全部通过。新增本项 **51项通过**，G2-01—03 **97项通过**，原后端 **53项通过**。对G2-03逐题逐轮比较：原36个全绿题全部保持，新增13个整题通过；原已通过轮次没有退化。原文35篇215块未覆盖0字符，15问75条来源错位0。

## 复现入口

在仓库根运行，输出路径使用新名字。复用 `starter/.venv`，不声称这是新装依赖的验收。

```bash
G2_EVIDENCE=/tmp/g2-04-review-http starter/.venv/bin/python -m pytest docs/verification/g2-04/test_doc_qa.py -q
G2_EVIDENCE=/tmp/g2-04-review-predecessors starter/.venv/bin/python -m pytest docs/verification/g2-01/test_ingestion.py docs/verification/g2-02/test_evidence.py docs/verification/g2-03/test_retrieval.py -q
starter/.venv/bin/python docs/diagnostics/2026-09-27-g2-start/baseline.py --repo "$PWD" --out /tmp/g2-04-review-integration
starter/.venv/bin/python docs/verification/g2-04/audit.py /tmp/g2-04-review-http /tmp/g2-04-review-answers.json
starter/.venv/bin/python docs/verification/g2-02/audit.py /tmp/g2-04-review-integration /tmp/g2-04-review-sources.json
starter/.venv/bin/python docs/verification/g2-03/audit.py /tmp/g2-04-review-integration /tmp/g2-04-review-retrieval.json
starter/.venv/bin/python docs/verification/g2-04/compare.py docs/verification/g2-03/integration/eval/report.json /tmp/g2-04-review-integration/eval/report.json /tmp/g2-04-review-comparison.json
```

`baseline.py`导出调用时的HEAD，记录精确commit；`--out`必须不存在。HTTP测试复用前序Runtime，复制源码、使用独立KB/.cache/VAR_DIR，执行公开 `python -m kbqa.rebuild` 后启动真实uvicorn并请求 `/api/chat`、`/api/trace`。明确移除三个LLM变量，health确认mock；无 `.env.live`、真实/付费模型或外部服务。仅两条异常诊断测试向隔离源码注入RuntimeError；普通RAG测试没有固定检索替身。原后端53项含既有mock fixture，仅作兼容回归。

## 八项验收映射

| # | 实际检查和命令 | 结果与证据 |
|---|---|---|
| 1 无Key公开C/V | 上述baseline原样运行55题；`test_document_facts`对公开题直接读取问题/检查 | `integration-restored/eval/report.json`及report.md：C01—C08、V01/V02共10题全绿，含response类型、事实、旧版排除、quote逐字与规范化400字、最多4份文档、answer上限、trace。没有改题库/评分器 |
| 2 文档路由 | `test_document_route` 11项（含S01），真实plan和data_evidence | `scoped-acceptance-http/`：退款、现在/周五、多少钱、迟到多久、充值赠送均doc且无数据查询；G2-03原安全入口保留 |
| 3 历史/版本边界 | `test_history_boundary` 5项：退款6/14→6/15、会员6/30→7/1、全角日期 | 旧退款7天/现行24小时，旧充值50元/现行60元，各自引用适用版本且排除另一版。V03原题完整运行，首轮过、第二轮追问仍失败，未把补充单轮当整题通过 |
| 4 真实连续引用 | `quotes`在每次build当时核对全文、实际非补位hit、chunk.source_text或context_spans；`test_quote_normalized_limit`；独立audit | HTML真实FAQ C05、GBK营业时间C03、表格C02（行+表头分别连续引用）；MD/HTML/GBK尾段均经过重建和HTTP。兼容字符428字反例按契约拒用。`scoped-acceptance.txt`、`scoped-answer-audit.json`；同一次索引替换前后分别检查，未用新快照冒充旧材料 |
| 5 缺答案/指令 | 3个缺单位事实、3个缺属性、弱相关费用；3个正常属性反例；S01及含指令的尾段夹具 | 手续费/申诉办结/花生含量/身份证/积分抵扣/花生属性缺证据时refusal且无引用；叠加/提现/审批正常答。文档内“忽略指令/回答9999999”不进答案/引用，evidence.rejected记录document_instruction；只承诺已测试的本关边界，不宣称完整安全体系 |
| 6 改写/换事实 | `test_rephrasing` 6项，`test_replacement_tail_and_instruction` 3格式×两次build/restart | 中文改写、英文别名、门店别名、跨语言赔付等真实回答；人工KB901夜班配送17→23小时，重建重启后答案/quote跟随，旧值不出现；原始KB未修改。没有题号/文档号/答案数值的产品分支 |
| 7 诊断/异常 | 54次HTTP问答取回54条trace；`test_error_trace`在planner/取证处分别抛错 | plan有路由/时点，search有实际query/候选分数/过滤，evidence有选句/拒用/原文范围/引用。合法HTTP200/refusal、trace.errors真实RuntimeError与堆栈、日志exception可查；`test_error_trace[plan]-server.log.txt`与`[evidence]-server.log.txt` |
| 8 前序及全量不退化 | 51项本项、97项前序、baseline53原后端和55题；逐题逐轮compare | `scoped-acceptance.txt`、`restored-predecessors.txt`、`integration-restored/backend-tests.txt`；metrics6/6、data12/12、retrieval15/15、refusal8/8，S02/S03及两库哈希门禁保持。`restored-comparison.md/json`：36保持、13新增、6仍失败，原通过轮次无回归 |

`scoped-acceptance`在最终业务代码上加强了逐次build的原文块/表头映射断言；此前`acceptance`也是同一业务代码的51项通过，均保留。`audit.py`独立核对响应约束、trace和正分非补位身份；原文逐字与准确片段范围由测试在每个实际输入快照中核对，包含17→23更新的两次快照。

## 红绿与试错

| 阶段 | 红灯提交/输出 | 修复及绿灯 |
|---|---|---|
| 基点真实HTTP | `a4647d8` red：23失败4通过 | 路由`ff6860b`：11通过；取证另分阶段 |
| 路由后取证与错误 | `74583d2` evidence-red：15失败1通过 | `b77de97` evidence-green：27通过；evidence-attempt保留首轮4失败（含一次注入目标未更新） |
| 改写/历史/尾段替换 | `3b552a9` extra-confirmed-red：2失败13通过 | `6d58a28` extra-green：42通过 |
| 缺属性与正常反例 | `c647296` attribute-controls-red：4失败2通过 | `d916238` attribute-green：48通过；attribute-attempt的2失败保留 |
| NFKC引用上限 | `9287808` quote-limit-confirmed-red：1失败，实际428字 | `94b41e0` quote-limit-green：1通过 |
| 自引入H05回归 | `be64b0f` h05-red：原题/改写2失败，score-comparison记录3→0 | `67b0f62` h05-green：13通过，完整复评恢复88.5；未新增混合编排 |

`test-authoring.md`区分产品失败与测试误填：旧退款期误写、注入目标改名、提交说明计数笔误、被低分门禁遮住的NFKC首探针，以及弱相关夹具注释纠正。原始日志均保留，没有覆盖历史输出。DEBUG_LOG逐项记录当时假设、实际实验、源码行号及修复提交。

## 全量分数与剩余边界

| 类别 | G2-03 | 本项最终 |
|---|---:|---:|
| metrics | 6/6 | 6/6 |
| retrieval | 15/15 | 15/15 |
| data | 12/12 | 12/12 |
| doc | 0/16 | 16/16 |
| version | 0/6 | 5/6 |
| hybrid | 6/18 | 12/18 |
| multi_turn | 2/9 | 4.5/9 |
| refusal | 8/8 | 8/8 |
| safety | 6/9 | 9/9 |
| health | 1/1 | 1/1 |
| 总分/全绿 | 56/100；36/55 | 88.5/100；49/55 |

首次`b77de97`和随后`94b41e0`均85.5分，保留在`first-integration/`及`integration/`。它们包含H05回归，不能作为最终无退化结果。最终`integration-restored/`对应`67b0f62`。
新增全绿为C01—C08、V01/V02、H02/H04、S01；H05恢复原通过。仍未全绿 **V03、H01、H06、T01、T02、T03**。V03/T02/T03部分轮次受基础修复影响提高，未实现会话继承/隔离，不能宣称多轮完成。H02/H04是共享路由恢复已有路径的结果，未据此实施第三关。

- 无模型回答是抽取式、以最强支持片段为核心；复用BM25与通用词项/焦点/单位/布尔属性规则。属性末尾词和0.6覆盖阈值是保守启发式，未声称任意同义改写或隐藏题都可靠；长于400规范化字符且无法短引的单元会放弃。
- 纯文档新路径不扫描整篇作事实。旧 `_doc_block` 仍用于后续混合文档侧拼接，未重写混合、会话或live引擎；不得将本项结果推广为这些路径都满足相同取证保证。
- 明确历史/政策问句保留as-of；非政策事件月份作事件主题，资料时点用today。未新增通用语言时间语义解析器。
- 复用既有指令识别规则，记录拒用而不改原文；不等于完整安全对抗。未改前端、部署、引入新服务或调用真实模型；G2-05未启动。

## 工作树、输入保护和资源

- 共享checkout `/Volumes/MACPSSD/project/moneki-ai-takehome`，分支 `codex/g2-04-doc-qa`；未新建worktree，未动其他三个管理checkout。
- `preservation.json`核对905个原始数据/KB/公开评测/旧基线/诊断/前序证据及既有未跟踪文件，变化0。原 `docs/baseline/2026-09-26-followup-draft.md`、`docs/research/`仍未跟踪，未吸收、改写或清理。
- `resources.json`列出所有自建测试服务的PID、端口、隔离源码和停止状态，全部由测试finally退出，无常驻自建服务。最终全量PID35667、端口59131，已停止；对应`integration-restored/environment.json`。
- 保留 `/tmp/moneki-g2-04-first-integration`、`/tmp/moneki-g2-04-final-integration`（85.5）和`/tmp/moneki-g2-04-restored-integration`（88.5），及JSON引用的pytest/source临时目录；未主动清理。pytest已自动回收部分较早临时目录，仓库内HTTP/trace及错误日志已保存；其他临时目录以后也可能被框架或系统回收。
- PR后等待主会话独立审查、合并决定及具体分支清理指令；执行会话不直接推main、不合并、不自行关闭Issue或开启下一任务。

## 提交前自查

按固定点核对业务diff，仅5个产品文件（116新增/27删除）；没有KB/题号/答案数值分支。最终交付的业务文件与67b0f62被测树一致。代码、测试脚本和Markdown的whitespace检查通过；完整diff仅9份真实pytest失败输出有尾部空白提示，保留原始输出不修剪，见final-checks.json。未发现尚未报告的本项合并阻塞；PR可合并状态不替代主会话独立验收。
