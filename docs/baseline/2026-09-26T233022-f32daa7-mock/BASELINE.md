# 原始 starter 基线（2026-09-26，本地无 Key）

## 范围与完成标准

固定点为 `main` / `f32daa70b8236429a0daad2090c6e91dc309deb6`。本次只运行原始重建、原有测试、完整公开评测和只读定位，不修业务代码、原始数据或题库。完成标准是输入不变、命令和配置可复现、原始结果与失败均保存；不要求 starter 得高分。

运行前工作树已有 `?? docs/research/`，该目录不属于本次工作。项目目录内没有现成的 `starter/.venv`、`starter/var`、`starter/.cache` 或 8000 端口监听。系统提供 Python 3.12.14、`uv` 和 `make`。Python 依赖来自未锁版本的 `starter/requirements.txt`，实际版本见 `dependencies.txt`。

`VAR_DIR` 只能隔离清洗库；`Settings.index_path` 固定指向 starter 目录中的 `.cache/index.json`。因此把 `starter/` 复制到系统临时目录，在副本中创建 `.venv`、重建和启动。源 `data/`、`knowledge_base/`、`eval/public_questions.jsonl` 仍从原 checkout 只读使用；输入的 SHA-256 清单见 `input-sha256-before.txt` 和 `input-sha256-after.txt`，两者逐字相同。临时副本是运行缓存，不是可长期保存的交付物；以下命令可用新的临时目录复现。

## 复现命令

在仓库根目录执行。`env -i` 明确清除继承的模型配置和 Key；仅传入列出的非秘密变量。原始运行使用未锁版本的 requirements.txt；下面的复现命令附加本次 dependencies.txt 作为版本约束，并使用新的输出目录，避免覆盖原始证据。依赖下载仍取决于包源可用性。

```bash
ROOT="$PWD"
BASELINE_EVIDENCE="$ROOT/docs/baseline/2026-09-26T233022-f32daa7-mock"
RUNTIME="$(mktemp -d /tmp/moneki-baseline.XXXXXX)"
cp -R starter "$RUNTIME/starter"
env -i PATH='/opt/homebrew/bin:/usr/bin:/bin' HOME="$HOME" /opt/homebrew/bin/python3.12 -m venv "$RUNTIME/starter/.venv"
env -i PATH='/opt/homebrew/bin:/usr/bin:/bin' HOME="$HOME" "$RUNTIME/starter/.venv/bin/python" -m pip install -r "$RUNTIME/starter/requirements.txt" -c "$BASELINE_EVIDENCE/dependencies.txt"
cd "$RUNTIME/starter"
env -i PATH='/opt/homebrew/bin:/usr/bin:/bin' HOME="$HOME" DATA_DIR="$ROOT/data" KB_DIR="$ROOT/knowledge_base" VAR_DIR="$RUNTIME/starter/var" make rebuild PY="$RUNTIME/starter/.venv/bin/python"
env -i PATH='/opt/homebrew/bin:/usr/bin:/bin' HOME="$HOME" DATA_DIR="$ROOT/data" KB_DIR="$ROOT/knowledge_base" VAR_DIR="$RUNTIME/starter/var" make test PY="$RUNTIME/starter/.venv/bin/python"
env -i PATH='/opt/homebrew/bin:/usr/bin:/bin' HOME="$HOME" DATA_DIR="$ROOT/data" KB_DIR="$ROOT/knowledge_base" VAR_DIR="$RUNTIME/starter/var" make run PY="$RUNTIME/starter/.venv/bin/python" PORT=53176
# 另一个终端，在仓库根目录；创建新的报告目录：
BASELINE_REPRO_OUT="$(mktemp -d /tmp/moneki-baseline-report.XXXXXX)"
env -i PATH='/opt/homebrew/bin:/usr/bin:/bin' HOME="$HOME" /opt/homebrew/bin/python3.12 eval/run_eval.py --base-url http://127.0.0.1:53176 --questions eval/public_questions.jsonl --out "$BASELINE_REPRO_OUT"
# 评测脚本自身测试：
cd eval/tests
env -i PATH='/opt/homebrew/bin:/usr/bin:/bin' HOME="$HOME" /opt/homebrew/bin/python3.12 -m unittest test_run_eval test_run_eval_public test_llm_gateway -q
```

本次端口 53176 是临时空闲端口；复现时可换用其他空闲端口。服务只绑定 `127.0.0.1`，本轮结束已停止。未调用真实模型或业务外部服务；环境准备从包源下载依赖，没有运行 LLM preflight。评测请求走本地服务，`/api/health` 确认 `llm_mode: mock`。`TODAY` 未设置，使用契约默认 `2026-09-01`。

## 原始结果

| 检查 | 结果 | 原始证据 |
| --- | --- | --- |
| 重建 | exit 0；清洗表 18,628 行全保留，索引 25 篇 / 53 片段 | `rebuild.output.txt`、`rebuild.exit` |
| starter 测试 | 17 passed，1 个弃用警告 | `starter-tests.output.txt`、`starter-tests.exit` |
| 评测器测试 | 260 tests，OK | `evaluator-tests.output.txt`、`evaluator-tests.exit` |
| 健康接口 | HTTP 200、`mock`；`kb_docs=36`、`valid_sales_rows=18628`、`data_period.start=""`、`end="N/A"` | `health.json` |
| 完整公开评测 | exit 0；17/100，55 题中 11 题全绿、44 题未全绿 | `eval.output.txt`、`report.json`、`report.md`、`failed-questions.tsv` |

评测分类：metrics 1/6，retrieval 6/15，data 0/12，doc 0/16，version 0/6，hybrid 0/18，multi_turn 1/9，refusal 6/8，safety 3/9，health 0/1。这里是**公开题库对原始 mock 模式**的分数；不代表真实模型、隐藏题库或最终产品表现。44 道失败题及每题失败检查项在 `failed-questions.tsv`，逐题请求、响应和判分理由在 `report.md` / `report.json`。例如 M01–M04、M06 的指标值不符，R01/R04/R05 的目标文档未入 top-5，N01 对 `kb_docs` 和 `valid_sales_rows` 均未通过。

## 已确认的代码行为与待验证因果

- `starter/kbqa/cleaning.py::clean_rows` 直接保留每行，未执行 KB-001 第 2、3 节要求的日期/编号规范化和六类顺序剔除。源库只读计数显示：18,628 行里有 143 行日期含 `/`、80 行符合 `DD-MM-YYYY` 形态、150 行金额为空、30 行数量转换后小于等于 0。计数有重叠，不能相加推导最终应保留行数。N01 期望 18,290 行，实际 18,628 行。
- `starter/kbqa/tools.py::query_metrics` 只查 `is_refund=0`，订单数用 `COUNT(*)`；这与 KB-001 的净营业额含退款、销售行订单去重定义不符。`data_period()` 对未规范化的文本日期取 `MIN/MAX`，得到空值与 `N/A`。这些是直接可见的源码行为；每一题的差额还需在修复任务里用红测试和查询核对。
- `starter/kbqa/loader.py` 仅将 `.md` / `.markdown` 纳入支持范围，原知识库含 `.txt` / `.html`。重建索引仅 25 篇，而评测器从知识库载入 35 篇；`/api/health` 直接数文件得到 36（含 README）。`starter/kbqa/tokenizer.py::tokenize` 仅按空白切词。两者是检索缺失的明确候选原因；R03 等单题还需核对版本、过滤与排序逻辑，不提前定论。
- starter 测试夹具在 `starter/tests/conftest.py` 固定替换 `Retriever.search`，所以 17 个测试通过不能证明真实知识库检索质量。公开报告还显示纯数据、纯文档、版本、混合、多轮和安全题失败；它们可能受到上游数据与检索问题牵连，不能把所有失败归为单一根因。

## 边界和未验证项

未做真实模型付费调用、DeepSeek 切换、preflight、浏览器端验证、隐藏题库、替换输入数据后的重建，亦未做 Git commit/push、PR、Issue 修改或部署。没有把公开题库中的期望数字写回原始数据或代码。`input-sha256` 对比与 `git diff --exit-code` 用于证明原始已跟踪输入和代码未改；`docs/research/` 仍是既有未跟踪内容。本次新增文件仅在这个独立证据目录。
