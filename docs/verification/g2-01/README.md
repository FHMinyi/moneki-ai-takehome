# G2-01 可信摄取与重建验证

Issue [#13](https://github.com/FHMinyi/moneki-ai-takehome/issues/13)。执行基线 `acfcabd5bf0fa69b8d54e4d948ee07a2f8a4a8ce`。
红灯提交 `ac14efd`（15失败），绿灯实现 `1e4ebbe`（15通过），后补别名/门店元数据真实 HTTP 检查，最终16通过。
所有子进程明确移除 LLM 三个环境变量，未加载 .env.live。服务输出为 mock。

## 复现命令

从仓库根运行；Python 复用已有 `starter/.venv`，本次不是重新安装依赖的验收。

```bash
G2_EVIDENCE=/tmp/g2-01-http starter/.venv/bin/python -m pytest docs/verification/g2-01/test_ingestion.py -q
starter/.venv/bin/python docs/verification/g2-01/capture_sources.py /tmp/g2-01-source-comparisons.json
starter/.venv/bin/python docs/diagnostics/2026-09-27-g2-start/baseline.py --repo "$PWD" --out /tmp/g2-01-fresh-integration
starter/.venv/bin/python docs/diagnostics/2026-09-27-g2-start/run_probes.py --baseline /tmp/g2-01-fresh-integration
```

`baseline.py --out` 必须是新目录；它导出调用时 HEAD。最后的诊断命令当前预期退出1，保留后续任务的真实失败；不能 xfail 或弱化为通过。前三条完成本项验证。
HTTP 回归复制 kbqa 源码到 pytest 临时目录，各自独立 `.cache` 和 VAR_DIR，执行 `python -m kbqa.rebuild`，再以 uvicorn 启动真实服务；未加载 starter/tests 的固定检索 fixture。
原后端检查在 git archive 导出中运行；其原有固定检索 fixture 未修改，因此只作为兼容性检查，不替代本项目新增 HTTP 证据。

## 七项验收映射

| # | 实际命令/测试 | 输出与证据 |
|---|---|---|
| 1 | `test_original_identity_and_formats`、`capture_sources.py`、集成 rebuild | 动态文件身份集合=实际索引35篇，含 TXT/HTML/GBK；README 不计数；`source-comparisons.json`、`integration/rebuild.txt` |
| 2 | `test_actual_gbk_exact_text`、`test_actual_html_visible_text`、`test_html_paragraphs_and_entities` | GBK全文与严格原解码相同；HTML原文/正文/连续引文、实体©与段落验证；`source-comparisons.json` |
| 3 | `test_format_through_rebuild_http` | 两种格式真实 rebuild + HTTP，mailtoken 命中有正分；`red-http/` 与 `green-http/`/`final-http/` |
| 4 | `test_lifecycle_rebuild_restart_http` 四分支、`test_metadata_alias_public_rebuild_restart` | 增改删换库计数、全文、真实返回跟随更新，旧事实不残留；别名/标题/门店同步更新及删除清空；`final-http/` |
| 5 | `test_first_start_and_legacy_cache_upgrade`、四生命周期中的重复 build 相等 | 首次启动无缓存可用；真实旧 bm25-3 夹具无需手工删缓存升级；重复同输入完整 payload 相同；`legacy-index.json`、`final-http/` |
| 6 | `test_empty_and_non_document_health`、各 HTTP 快照及原始库集成 health | 空库0篇/0片段可启动，retrieve=[]；实际库35/88，计数等于索引；`integration/health.json` |
| 7 | pytest、baseline、run_probes | 本项15失败→15通过，最终16通过；原后端53通过；metrics6/6、data12/12；全量43/100、27/55；剩余探针7失败/12通过，见下 |

## 范围与剩余失败

`integration/eval/report.md` 保存全部55题：retrieval8/15、doc0/16、version0/6、hybrid3/18、multi_turn2/9、refusal8/8、safety3/9、health1/1。
本项没有完成中文检索和单轮文档问答。`integration/probes-1.txt`/`probes-2.txt` 两次均7失败/12通过，剩余 D04/D05/D06/D07/D08 留给后续 Issue。
`integration/audit.json` 表明35篇全部还有分块尾段损失，累计5940字符，且若干返回来源仍错位；全文已入索引不代表全部片段可检索。小库短正文及明确词项仅隔离 G2-01，不用它证明自然问句排序。

HTML 提取静态正文、块边界和实体，忽略 head/script/style/template；不执行 JS 或解析 CSS 布局。严格 UTF-8（含 BOM）和 GBK 覆盖实际输入；其他非法编码会显式失败，无通用编码猜测。知识库变更期间不保证在线一致性，沿用停止修改、重建、重启流程。
没有修改公开题库、评分器、原始数据、知识库、旧基线与启动诊断；保护清单及校验见 `protected-before.json`、`preservation.json`。

## 资源与证据

- 集成被测代码为 `1e4ebbe`；后续只增测试/记录，没有再改业务代码。
- `integration/environment.json`：源码导出路径、命令、PID 80810、端口51415；已终止。
- `red-http/`、`green-http/`、`metadata-http/`、`final-http/`：每次启动的实际 PID/端口/源码路径/health/retrieve/停止状态；统一摘要 `resources.json`。所有测试自建进程在 finally 中退出，无保留监听服务。
- 保留 `/tmp/moneki-g2-01-integration` 和 environment.json 对应源码副本及 pytest 临时副本；不主动清理。仓库内的 JSON/日志足够审查，临时路径以后可能被系统回收。
- 共享工作树 `/Volumes/MACPSSD/project/moneki-ai-takehome`、分支 `codex/g2-01-ingestion`；未创建其他 worktree。
- 原有 `docs/baseline/2026-09-26-followup-draft.md`、`docs/research/` 未跟踪且未改动。提交 PR 后等待主会话核验、合并及明确清理指令。
