# G2-02 完整证据与来源一致性

规格：[Issue #14](https://github.com/FHMinyi/moneki-ai-takehome/issues/14)。固定评审基点 `8b72f47f712eab309bcc5e65841acfce45f0e17e`。
实施完成，等待主会话独立核验；本文不是 Issue 验收关闭声明。

## 提交与真实红绿

| 缺陷/检查 | 红灯 | 修复与绿灯 |
|---|---|---|
| 丢尾段、表格截断、无连续位置/布局信息，空正文误用标题 | `b0244ce`：`chunk-red.txt` 11失败/3通过，`chunk-red-http/` | `2e4c2e4`：`chunk-green.txt` 14通过 |
| 去重后覆盖来源编号 | `b5a94c5`：`identity-red.txt` 2失败，独立夹具和真实R08 | `d4995b3`：`identity-green.txt` 16通过，R08/R10、去重重排和补位 |
| 初版新分块产生空白片段、标题脱离下一段 | `c1a9acb`：`spacing-red.txt` 1失败；首轮真实库360片段，其中20片段仅空白 | `b1d57c8`：`spacing-green.txt` 19通过，最终实际库215片段，无空白片段 |

`9e51f48` 加强了实际旧代码自动缓存升级、参数变化、局部标题、长表格行、15道检索的检查。
编写加强测试时发生一次转义错误（Python字符串被生成成真实换行），收集阶段语法错误保留于 `test-authoring-error.txt`；修正后18通过，不把它当产品红灯。
前两组原始红绿输出均未改写。`legacy-layout.json` 是执行基点实际生成的旧布局，早期测试使用；最终迁移测试直接导出固定基点的 index/chunker 在同目录生成旧缓存，随后恢复新实现，自动启动验证，无需人工重建。

## 可复现命令

从仓库根运行，复用 `starter/.venv`，不是新装依赖验收。输出目录请使用新名字，避免覆盖既有证据。

```bash
G2_EVIDENCE=/tmp/g2-02-review-http starter/.venv/bin/python -m pytest docs/verification/g2-02/test_evidence.py -q
G2_EVIDENCE=/tmp/g2-02-review-ingestion starter/.venv/bin/python -m pytest docs/verification/g2-01/test_ingestion.py -q
starter/.venv/bin/python docs/diagnostics/2026-09-27-g2-start/baseline.py --repo "$PWD" --out /tmp/g2-02-review-integration
starter/.venv/bin/python docs/verification/g2-02/audit.py /tmp/g2-02-review-integration /tmp/g2-02-review-audit.json
```

测试沿用 G2-01 的隔离 Runtime：复制源码到临时目录，独立 `.cache` 和 `VAR_DIR`，执行公开 `python -m kbqa.rebuild`，启动 uvicorn 并发送真实 HTTP。不导入 starter/tests 固定检索 fixture；每个服务在 finally 中退出。移除 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`，未读取 `.env.live`。
`baseline.py` 导出调用时 HEAD，所以复现最终保存结果使用 `b1d57c8`；后续提交只增加证据/说明，业务代码不变。
旧启动诊断的“直接拼接等于全文”探针不适用于允许 overlap 的布局；未改写它，新审计按原文位置覆盖集合检验。

## 六项验收证据

| # | 命令对应测试/审计 | 实际结果与文件 |
|---|---|---|
| 1 完整覆盖 | `test_boundary_full_coverage`、`test_actual_corpus_coverage`、`audit.py` | 长度0/1/299/300/301/599/600/601/900/901；真实35篇215片段，未覆盖0字符。`spacing-green-http/coverage.json`、`audit.json`含每块原文区间 |
| 2 尾段与多行表格 | `test_tail_fact_http`、`test_table_context_and_contiguous_quotes_http`、`test_context_is_local_and_rows_are_atomic` | 尾段7度、40行表格末行77均经真实HTTP正分命中；表头/标题定位同文档，长行完整；`spacing-green-http/` |
| 3 来源一致 | `test_duplicate_rerank_padding_identity_http`、`test_original_r08_r10_identity_http`、`test_actual_all_retrieval_identity_and_rebuild_stability`、`audit.py` | 同文档至少3个高分候选，去重/重排/正分及零分补位逐项核对；真实15问75条返回正文、doc/chunk及内部meta一致，错位0 |
| 4 检索与引用分离 | 表格测试及 `audit.py` | `Chunk.text` / `Hit.text` 为检索文本；HTTP `text` = 连续 `source_text`，另给 `retrieval_text` 和 `context_spans`；真实 DocFacts.cite 接受连续表格行，拒绝合成标题表头加末行 |
| 5 身份排序与缓存 | `test_offsets_context_and_cache_layout`、重复构建/HTTP测试 | 同输入完整缓存payload一致、ID/排序重复；旧基点代码生成的缓存自动升级；CHUNK_SIZE变化自动失效；health实际215片段，未硬编码 |
| 6 前序回归与真实材料 | 本项pytest、前序pytest、baseline | 19通过；G2-01 16通过；原后端53通过；真实HTTP及原始红绿保留。`g2-01-final.txt`、`integration/backend-tests.txt` |

## 接口和设计说明

- 偏移 `source_start`/`source_end` 是加载后的连续可见正文的 Python Unicode 字符下标，半开区间；不是磁盘字节偏移。HTML对应加载后的可见正文，Markdown不包含 front matter。
- HTTP 必有字段路径和类型保持不变。`text` 可直接追溯连续原文；新增 `retrieval_text` 明示合成检索上下文，`context_spans` 中每条标题/表头带同篇正文位置；文档元数据标题可用于检索，不能假冒正文引用。
- 300字符是目标大小；长普通行使用60字符 overlap。优先段落/换行边界，Markdown pipe table保留整行；一行超过目标大小时保留整行。标题层级只继承当前父级，表格之外不继承旧表头。空正文不制造标题证据。
- `chunker-4` 与大小/overlap参数进入缓存键；改变其他布局语义仍需升级版本。相同输入可复现，不承诺文档编辑后仍沿用旧 chunk_id。
- 保留BM25及现有去重/补位策略。中文排名、现行/历史版本过滤、过滤后top-k、问答路由和聊天引用选择属后续任务。本项没有证明这些行为通过。
- Markdown解析只覆盖ATX标题与pipe表格，不是通用Markdown AST（如Setext标题、复杂合并单元格）。HTML继续沿用G2-01可见正文提取；未新增网页渲染或HTML表格结构恢复。

## 集成结果和边界

最终集成实际被测提交：`b1d57c820a301c8c2a2a55a51b2aeb5335905d30`。
`integration/` 保存最终报告；`integration-before-spacing/` 保存 `9e51f48` 的首轮结果（360片段），未覆盖旧输出。
最终无模型 **44/100，28/55题全绿**：metrics6/6、data12/12、retrieval9/15、doc0/16、version0/6、hybrid3/18、multi_turn2/9、refusal8/8、safety3/9、health1/1。
相比G2-01的43分增加1分，指标和数据题保持通过；总分和零分补位不作为相关性验收证明。不代表第二关完成、隐藏题或真实模型通过。

## 资源与保护

- 共享checkout `/Volumes/MACPSSD/project/moneki-ai-takehome`，分支 `codex/g2-02-evidence`；未新建worktree、未动另外三个管理worktree。
- `preservation.json`：324个原始数据/KB/公开评测/旧基线/诊断/前序证据和未提交材料逐文件SHA-256无变化。原有 `docs/baseline/2026-09-26-followup-draft.md`、`docs/research/` 保留未跟踪。
- `resources.json`汇总77次短期测试服务的PID、端口、证据和退出状态，全部已退出。最终集成PID85747/端口53661；首轮PID84995/53316。没有常驻服务。
- 保留 `/tmp/moneki-g2-02-final`、`/tmp/moneki-g2-02-integration` 及环境JSON指向的源码/pytest临时目录；没有清理临时产物。仓库内日志足够复查；系统以后可能回收临时目录。
- 无部署、无付费调用、未加载 `.env.live`；不自行合并、关闭Issue或启动后续任务。等待主会话审查/清理指令。
