# G2-04 follow-up：正文与显式标题身份

来源：重开的 [Issue #16](https://github.com/FHMinyi/moneki-ai-takehome/issues/16) 第6项，以及G2-05检查点 `d2a25c2585f7eb680bbffa06577a40f5966cebe0`。原PR21历史不修改，本次单独修复。

**固定点 `358859a5be641b04395f314029e4b9325631dd8a`；最终被测业务提交 `31d2c648c8fb6849514a2a59d3d034b579ee39f4`。** 原G2-05两脚本未改字节/输入/断言，在该精确提交上均全绿：A/B四问通过，生命周期五阶段七问通过。新增20项、前序179项、原后端53项通过；公开无模型仍88.5/100、49/55，原通过题和轮次没有回归。等待主会话独立核验和合并；不自行关闭Issue、清理或启动G2-05。

## 根因和最小实现

原材料只有“翡翠饭的配送时限为31分钟。”，loader把首句推断成展示标题；chunk.heading包含该标题，units以文本相等将真正正文标成heading，docfacts.rank又将它排除。原始检索有正分且source_text正确，问题出在句子身份，不是别名展开失败。

产品改动仅 `loader.py` 和 `units.py`（80新增/15删除）：

- 展示/检索用的document.title保持原有推断逻辑，不能凭它与正文同名就删正文。
- Markdown标题身份使用已有context_spans的原文位置；多句和跨窗口的同一个标题均保留结构身份，长标题不与下一行正文合并。纯TXT里的井号是原文，不按Markdown标题处理。
- HTML在现有静态可见正文解析器中附加h1—h6的可见原文范围；不改变可见文本归一，不引入新解析器或渲染服务。
- 去重保留heading/text的身份差异，因此相同文字在标题和正文各出现一次时，正文仍可作为证据。
- metadata新增可选heading_spans，位置均为可见正文Unicode字符下标；旧字段、Chunk schema、context_spans和原文内容不变。loader-4使旧磁盘索引自动重建；旧缓存测试用真实358859a loader/units生成，再恢复新实现启动，没有手工删缓存或补标题。

没有修改planner、置信度阈值、别名词表、语言规则或第三关路径。

## 可复现命令

在仓库根运行，使用新的输出目录；复用已有venv，不声称本次重新安装环境。所有HTTP均为隔离源码/KB/.cache/VAR_DIR，公开rebuild、真实uvicorn、禁用LLM配置，不加载.env.live。

```bash
G2_EVIDENCE=/tmp/g204-heading-review-http starter/.venv/bin/python -m pytest docs/verification/g2-04-heading-fix/test_heading.py -q
G2_EVIDENCE=/tmp/g204-heading-review-prior starter/.venv/bin/python -m pytest docs/verification/g2-01/test_ingestion.py docs/verification/g2-02/test_evidence.py docs/verification/g2-03/test_retrieval.py docs/verification/g2-04/test_doc_qa.py -q
starter/.venv/bin/python docs/verification/g2-04-heading-fix/replay_checkpoint.py --source "$PWD" --evidence /tmp/g204-heading-review-checkpoint
starter/.venv/bin/python docs/diagnostics/2026-09-27-g2-start/baseline.py --repo "$PWD" --out /tmp/g204-heading-review-integration
starter/.venv/bin/python docs/verification/g2-02/audit.py /tmp/g204-heading-review-integration /tmp/g204-heading-review-sources.json
starter/.venv/bin/python docs/verification/g2-03/audit.py /tmp/g204-heading-review-integration /tmp/g204-heading-review-retrieval.json
starter/.venv/bin/python docs/verification/g2-04/compare.py docs/verification/g2-04/review-r1-integration/eval/report.json /tmp/g204-heading-review-integration/eval/report.json /tmp/g204-heading-review-comparison.json
```

`replay_checkpoint.py`从Git检查点d2a25c2读出G2-05脚本，不改源码，记录SHA；运行前逐文件比对被测产品字节与声明提交。默认用当前HEAD，也可用`--commit <ref>`验证导出的源码。原始脚本SHA如下，`checkpoint-final/commands.json`同时保存29个产品文件SHA、精确提交、完整实际命令及退出码。

- reproduce_heading.py：`6014f8ce3e5dfb817e1a67ac8cc63b8264aa857f8d3217dde1f8b0c766b19add`
- verify_kb.py：`8685a25a932ea1536cc037c88d103c4b06c65d73b20fa99acf2394634c8898ab`

baseline.py导出调用时HEAD，environment.json记录实际被测提交。后续只整理文档的交付提交与31d2c64业务字节一致。

## 验收证据

| 范围 | 实际结果 | 文件 |
|---|---|---|
| 原始A/B最小复现 | 无标题/显式标题 × 中文/英文别名，4条retrieve+chat全过；均精确连续31分钟引用 | checkpoint-final/ab/http.json、stdout.txt及inputs |
| 原始替换生命周期 | 初始无标题MD、新增HTML、改GBK TXT及别名、删HTML、换目录，5阶段7问全过；旧事实和旧别名淘汰实际执行 | checkpoint-final/lifecycle/result.json、http.json、input-snapshots |
| 无标题格式/更新 | MD、UTF8 TXT、GBK TXT、HTML，各31→47更新及中英文问法均正确 | final-unit.txt 20通过及final-unit-http |
| 真标题和位置 | 标题本身不作事实；标题/正文同名不吞正文；元数据标题不决定正文身份；多句/跨窗口Markdown与HTML内联标题过滤；连续来源及HTML偏移核对 | test_structural_heading_controls、test_true_heading_sentences_and_windows等 |
| 缓存兼容 | 用358859a真实旧loader/units生成缓存，新实现直接启动，正文可答、标题仍不当事实 | test_actual_old_cache_preserves_prose_and_heading_identity；HTTP与前后key记录 |
| 原G2-01—04回归 | 16+19+62+82=179全部通过，包含历史边界、引用、近主题拒答、H05及S02/S03门禁 | predecessors.txt、predecessor-http |
| 全量与原后端 | 53原后端通过；55题无模型88.5/100、49全绿；C01—C08/V01/V02保持，所有原已通过题/轮次保持 | integration/eval/report.json、report.md、backend-tests.txt；comparison.json/md |
| 来源/完整性 | 35篇215块、原文遗漏0；15问75条来源错位0、检索15/15 | source-audit.json、retrieval-audit.json |

## 红绿、真实试错与范围收敛

- `04b435d`先保存15项真实HTTP **11失败4通过**；原G2-05两脚本在checkpoint-red原样退出1，A/B两条无标题chat失败，生命周期4失败1通过。
- 首轮实现把heading_spans默认值初始化放错函数，重建报UnboundLocalError；`green.txt`虽然名称含green，实际是15失败。`first-attempt.patch`保存当时未提交的产品差异，后修正初始化位置。不得把它算绿灯。
- `3dc0d3f`保存正文身份修复及原两脚本首次全绿；15项中14过，剩余是自增长标题英文低分拒答。该次checkpoint-first-fix在提交前候选上执行，commands的旧HEAD04b435d不冒充精确提交验收；最终以checkpoint-final的31d2c64及逐产品文件SHA为准。
- `4f95a04`保存Markdown多句/跨窗口真标题的候选身份红灯；`31d2c64`用已有context_spans位置修正。最终20项结构测试通过。
- 自增长标题英文问句原来要求一定doc。正文修复后已选中正确31分钟原文，但最高分6.6644触发现有CLARIFY_SCORE=8/underspecified门禁。主会话明确该自增回答率假设不是此次最小修复的新门槛：保留原问句、材料和失败输出，只将这项控制收敛为“正文进入候选且来源连续”；允许现有refusal且不得有引用。没有降低阈值、扩词表或改G2-05原断言。前后版本与理由见expectation-scope.md。

这条长标题英文问题仍可能保守拒答，不能声称任意标题/问法都可回答。Markdown仍沿用已有ATX结构范围，未扩为完整Markdown AST；HTML沿用静态HTMLParser并标注正常h1—h6结构，未实现浏览器级容错解析。剩余公开失败V03/H01/H06/T01—T03及第三关范围不变。

## 工作区、保护和资源

- 从358859a建立 `codex/g2-04-heading-fix`，未合并G2-05证据提交。G2-05本地/远端分支仍为d2a25c2，证据tree仍83058f994c9a869d221d51e13f4ab578d7e3a4b3；G2-05继续等待协调。
- preservation.json：2146个原数据/KB/题库评分器/旧基线与证据/原未跟踪材料无变化。原草稿和docs/research/保持未跟踪，其他三个管理checkout未动。
- resources.json：290次本任务自建服务均由finally退出。最终全量PID10031、端口55566已停止，无常驻自建服务。
- 保留`/tmp/moneki-g204-heading-integration`、checkpoint-final/commands.json指向的专属replay工作目录和源码、pytest副本。未主动清理，也未动G2-05原服务/环境/材料；较旧pytest目录可能被框架自动回收。
- 未加载.env.live、未付费、未部署、未推main/force push、未自行合并/关闭Issue或启动后续任务。
