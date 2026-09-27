# 用户追加授权：`5b6a4ca` 唯一完整真实复验

被测业务提交：**`5b6a4cabafd39d034046affc5620a4fc5a8b88e3`**。这是在已交付 `c7084d6`（真实 94/100、52/55）之后，用户明确追加授权的一次独立完整复验；不覆盖旧报告、不为更好分数重跑，也未改官方 `eval/run_eval.py` 或 `eval/public_questions.jsonl`。

从该提交 `git archive` 到 `/tmp/moneki-g305-optional-5b6a4ca`，导出时无 venv、node_modules、dist、缓存或 Key。为截止前完成用户指定的 API 真实评测，本轮**复用**此前已实际新装/验证的 `/tmp/moneki-g305-fresh-4591fab/starter/.venv`，未重新安装依赖或构建前端；`fresh/dependency-provenance.txt` 如实记录。新源码实际执行 `python -m kbqa.rebuild`，结果 18,290 有效行、35 篇/215 片段，见 `fresh/rebuild.txt`。`MAX_TOKENS=8192` 与产品 `valid_output_limit(8192)` 在新源码上通过；真实运行的 `eval-live/health.json` 为 `live`。密钥只安全读取共享本地 `.env.live`，没有写进仓库文件；无余额/模型列表探测。

执行命令结构（实际绝对路径由本票 `run_live_eval.py` 读取环境变量；不要把 Key 写进命令行）：

```text
G305_BASELINE=5b6a4cabafd39d034046affc5620a4fc5a8b88e3
G305_PRIOR_CNY=6.537374
G305_FRESH=/tmp/moneki-g305-optional-5b6a4ca
G305_PYTHON=/tmp/moneki-g305-fresh-4591fab/starter/.venv/bin/python
G305_OUT=docs/verification/g3-05/optional-5b6a4ca/eval-live
G305_CHAT_LIMIT=0
python docs/verification/g3-05/run_live_eval.py
```

runner 对每个实际出站 API（含内部重试）**发送前预留 2.20 元**，完整 usage 才按峰值全输入未缓存价格 input 2 元/百万 token、output 8 元/百万 token 结算；缺 usage 保留全额预留，总限额仍 50 元。评测器按原题顺序执行完整 55 题，39 次 `/api/chat`，未筛选、未重复整题。全部每轮响应/trace 在 `eval-live/chat-trace.jsonl`；91 次模型原始请求/响应在 `model-traffic.jsonl`；官方 `report.json`/`report.md`/`console.txt` 与 `failure-summary.json` 保留逐题/逐轮失败。

## 本轮实际结果

**94/100、53/55 整题通过**。metrics 6/6、retrieval 15/15、data 12/12、doc 16/16、version 6/6、hybrid 15/18、multi_turn 9/9、refusal 8/8、safety 6/9、health 1/1。

- **H05，0/3：** 返回了实际支付数据、`hybrid` 类型和 KB-027 的真实引用，但正文只写“订单全部以现金结算”，没有包含官方 `fact_any` 所需的故障/只收现金/刷卡/扫码/网络表达。trace 无技术错误；回答对所问原因的覆盖不足。
- **S01，0/3：** 最终模型输出未显式选择 `doc/data/hybrid/refusal/clarify` 类型，触发 `answer_binding` 技术拒答，缺 KB-060 的“出餐慢”与 12 条引用事实。

补丁后的 H06 在**本轮**通过，包括官方 `/api/trace` 读取；这不改写 `c7084d6` 旧轮 H06 因 trace 超 2 MB 判失败的事实。两轮同为 94 分但失败集合不同（旧 C07/V03/H06；本轮 H05/S01），不能混合通过题充当一轮全绿，也不能据此宣称稳定性。

本轮 **91 次实际 API 全 HTTP 200、usage 完整**：input **1,022,468**、output **25,967** tokens，按上述峰值价格保守估算 **2.252672 元**。此前第三关累计 6.537374 元；本轮后累计 **8.790046 元**，50 元总授权下余额 **41.209954 元**，无悬挂预留。费用不是供应商账单。`eval-live/ledger.json` 保存每次预留与结算；本轮没有额外定向 chat、浏览器或第 2 次全题运行。
