# G3-04 显式日期范围修复

固定起点 `4591fab9a80ef63c440b9a117dbbc4fcbf03c430`，指定独立托管树初始 clean。G3-05 的原始替换证据 `docs/verification/g3-05/replacement/scope-defect.json` 与脚本 `docs/verification/g3-05/run_scope_defect.py` 位于 G3-05 执行树，仅读取、不修改。本目录只保存本票新验证输出。

## 起点与根因

- 改动前原后端 `53 passed`、G3-04 会话测试 `18 passed`，分别见 `baseline-original-backend.txt` 和 `baseline-session.txt`。
- 自包含替换 fixture 复制现有 SQLite 与 KB 后，清空销售表，写入 6 月 18 日同商品销售 9 件/退款 2 件、7 月 1 日额外销售 5 件，并在 KB-003 给牛肉poke新增测试别名。独立 SQL 得到 6 月 18 日应为 **7 件**，精确日 `/api/metrics/summary` 也为 7；旧 `/api/chat` 把跨日 5 件合并，返回 12 件。`red-date-scope.txt` 为 7 failed、2 passed。
- 逐层定位：`normalise('S02 6月18日…')` 保留空格，而 `parse_time` 无条件删除空格，使其变成 `s026月18日…`；月份正则先吃到非法 `26月`，时间窗口消失，Planner 使用数据全集。标准商品名替换测试别名也会发生同样错误，故缺陷与新别名本身无关。

## 修复与边界

时间解析只保留用户**实际写出的**字母数字编号与数值日期之间的空白边界，日期内部空格仍按原行为压缩；不猜测 `S026月` 应拆成 `S02 + 6月`。这种连续三位编号被当作未知门店并拒绝，避免静默改成全部门店。该处理不增加题号、别名或答案特判，不改变正常无日期请求使用数据全集的行为。

纯查数问题中，只有**用户原问题自身可独立解析的单个精确日**成为受控 live 工具的硬范围。受控模型先请求 6 月 18 日至 7 月 1 日时工具返回错误；改为 6 月 18 日单日后，真实 SQLite 返回 7 件，最终回答只引用该成功调用。无日期请求仍可查全部有效数据，两区间比较仍可使用 `compare_periods`；月/粗时间提示及混合解释不被此新增硬范围限制。趋势引用仍按已有规则由用户文字指定的新日期覆盖。

## 可复验结果

| 命令/证据 | 结果 |
| --- | --- |
| `.venv/bin/python -m pytest docs/verification/g3-04/date-scope-repair/test_date_scope.py -q` | `green-date-scope.txt`，12 passed；含原替换输入、标准名、空格/相邻、日/号、未知连续编号拒绝、跨日期5件、历史追问/趋势覆盖、无日期全集、两期比较与受控 live 越界拒绝 |
| `.venv/bin/python -m pytest starter/tests -q` | `green-original-backend.txt`，53 passed，独立进程避免原夹具全局假检索污染 |
| `.venv/bin/python -m pytest docs/verification/g3-01/test_data_chat.py docs/verification/g3-02/test_document_binding.py docs/verification/g3-04/test_session_context.py docs/verification/g3-06/test_trend_context.py docs/verification/g3-06/test_early_plan_context.py -q` | `green-cross-stage.txt`，95 passed，基于起点主干 |
| `G304_DATE_HTTP_OUTPUT=docs/verification/g3-04/date-scope-repair/actual-http-final.json .venv/bin/python docs/verification/g3-04/date-scope-repair/replay_http.py` | `actual-http-final.json`，独立 uvicorn/真实 HTTP 四组请求、响应、完整 trace：精确日7、邻日5、无日期全集12、趋势旧日被问句新日覆盖为7 |

不部署、不调用付费模型，不修改 G3-05 的替换输入或官方评分器。首次业务提交后已 normal merge 最新主干并复验；跨票集成结果单列记录。

与 G3-02 PR #36 合并后的独立集成记录见 [integration-8132f/README.md](integration-8132f/README.md)。
