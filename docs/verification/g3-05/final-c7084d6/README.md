# G3-05 最终集成固定点验收（2026-09-27）

业务提交 **`c7084d6f841d150c6672410719a4785b4a7696b1`**，含 G3-02 文档协议/8192 输出、G3-04 日期修复和 G3-03 最终混合修复。G3-05 分支正常合并该 main，不改 `starter/`、`frontend/src/`、`data/`、`knowledge_base/`、`eval/` 业务与评分器；历史 `4591fab` 失败与账本在上级目录原样保留。

源码用 `git archive c7084d6` 单独导出至 `/tmp/moneki-g305-final-c7084d6`，初始无环境、缓存、dist、凭证。为了截止前收口，此轮**复用**此前两个已实际新装并验证的 Python venv 与 npm node_modules，未把复用称为再一次 fresh 安装；依赖来源见 `fresh/dependency-provenance.txt`，此前真实安装完整日志在 `../fresh/`。本次从新源码实际重建 18,290 行、35 文档/215 片段并执行 Vite 构建，原始输出在 `fresh/rebuild.txt`、`fresh/build.txt`；平台与输入 SHA-256 在 `fresh/`。后端用复用 venv 从该新源码目录启动，无 Key health 为 mock，`fresh/key-path.json` 保存免费关键路径与原问题 trace。

## 一次真实定向与完整官方复验

第三关先前按 usage 估算累计 3.458894 元，50 元总授权下余 46.541106 元。所有上游实际 API（含可能的重试）发送前由本地执行守卫占用 **2.20 元**；本轮固定产品 `valid_output_limit` 只允许整数 1–8192。完整 usage 后按峰值全输入未缓存价格输入 2 元/百万、输出 8 元/百万结算，缺 usage 保留预留。密钥只从共享本地 `.env.live` 读入内存，不写进证据；没有余额/模型列表探测。金额均为保守估算，非供应商账单。

获批的两次定向中，①主动引用 S03 6/8–14 趋势，问“这段时间的净营业额为什么比前一周低？”。在**零费用受控真实 HTTP live 路径**，模型提出前周与本周的 `compare_periods` 后，产品范围守卫明确返回“比较查询与文字明确指定的有效条件不一致”，`fresh/controlled-prevweek.json` 保存请求/trace。该项未发送真实模型请求，剩余一个定向名额未用；不能把受控失败记成真实模型失败。②真实 Chromium 新会话问“外卖订单退款审核通过后，退款多久能到账？”，HTTP 200 `refusal`，但属于两次 `search_kb(top_k=15)` 超工具上限后的 `tool_failure`，不是证明模型区分“申请窗口/到账时间”的语义成功。`target/policy-browser.json/png`、`target/model-traffic.jsonl`、`target/ledger.json` 保存全貌；1 chat、7 API 均 HTTP 200+usage，input 156,937/output 1,090，估算 **0.322594 元**，累计 **3.781488 元**。没有重试整次 chat 或悄悄补第 2 个样本。

随后仅运行**一次**未经修改的 `eval/run_eval.py` + `eval/public_questions.jsonl` 完整真实 DeepSeek `deepseek-flash` 55 题，按原顺序保留每个多轮 turn。固定 `c7084d6`，health live、`max_tokens=8192`。命令和原始输出在 `eval-live/console.txt`、`report.json`、`report.md`；`chat-trace.jsonl` 保存每个 chat/trace，`model-traffic.jsonl` 保存每次实际出站请求及原始响应，`failure-summary.json` 只索引失败、不删除原数据。

| 分类 | 得分 / 满分 | 整题通过 |
| --- | ---: | ---: |
| 指标 / 检索 / 纯数据 | 6/6、15/15、12/12 | 6/6、15/15、6/6 |
| 纯文档 / 版本 | 14/16、5/6 | 7/8、2/3 |
| 混合 / 多轮 | 15/18、9/9 | 5/6、3/3 |
| 拒答 / 安全 / 健康 | 8/8、9/9、1/1 | 4/4、3/3、1/1 |
| **总计** | **94/100** | **52/55** |

失败 C07（0/2）：模型最终选择了不合法的 data 结果引用，`data_binding` 技术拒答；V03（1/2）：第二轮实际检索到 KB-010 后仍以 typed `insufficient_evidence` 拒答；H06（0/3）：`mixed_binding` 在工具失败后拒绝把原因说成“未知”，且 `/api/trace` 正文**超过官方评测器 2 MB 上限**，导致 `trace_required` 同轮失败。逐条检查和原错误见 `eval-live/failure-summary.json` 与原报告，不能用 94 分掩盖这三项。首轮 `4591fab` live 为 67.5/100、40/55；新旧代码/输出额度不同，新结果是独立复验，不是覆盖或择优挑选。

完整复验共 **102 次实际 API**，全 HTTP 200 且 usage 完整：input **1,262,771**、output **28,793** tokens，本轮保守估算 **2.755886 元**。加此前 3.781488 元，第三关累计 **6.537374 元**、50 元授权剩余 **43.462626 元**，无悬挂预留。账本在 `eval-live/ledger.json`。没有再跑付费全题或挑选最好结果。

未验证：隐藏题、两个交错的真实模型会话、真实模型对替换 DB/KB 的泛化、①真实浏览器趋势对比，以及任意自然问法的稳定语义选择。现有三宽无 Key Chromium、替换材料和安全受控证据仍按 `../README.md` 的原固定点标注，不移称本版本实时浏览器通过。第四关按用户选择只提供现有 trace 的现场调试流程（`docs/DEBUG_WORKFLOW.md`），没有新调试面板。
