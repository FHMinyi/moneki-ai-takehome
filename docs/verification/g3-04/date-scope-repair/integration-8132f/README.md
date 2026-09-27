# G3-04 日期修复与 G3-02 新文档协议集成

本票业务提交 `df27d0d414a2d053482f8db8c86c2a9d78ca5172` 固定后，从远端获取 `origin/main=8132f035cf4ca394fd9d04bd1fc19fd6810f581a`，使用普通 `git merge --no-ff --no-commit origin/main` 纳入 G3-02 PR #36 的同次模型选证、源内容验证与 8192 输出上限。无冲突，未 rebase。合并后的工作树上分别运行以下检查，均不调用付费模型：

| 验证 | 结果 |
| --- | --- |
| 日期替换测试 `test_date_scope.py` | `date-scope.txt`：12 passed，精确日、相邻行、未知连续编号、趋势/历史和受控 live 正反 |
| 原后端 `starter/tests` | `original-backend.txt`：53 passed，独立进程 |
| G3-01 数据、G3-04 会话、G3-06 趋势/早退 | `data-session-trend.txt`：56 passed |
| G3-02 新协议的源/范围/结构与输出上限 | `doc-minimal-protocol.txt`：49 passed；含实际本地 HTTP，验证同次模型选取的真实源片段与 8192 上限 |
| 替换库独立 uvicorn HTTP | `actual-http.json`：4/4，精确日7件、邻日5件、无日期全集12件、趋势附件旧日被显式新日覆盖为7 |

G3-02 已明确取消旧的 17 条语义绑定断言作为新协议门禁，本次没有把该旧套件伪称通过。G3-03 混合修复仍并行，由主会话决定后续顺序和再集成。未部署、未修改 G3-05 原替换证据、未调用真实模型。
