# G3-04 连续追问验证

固定起点：`eb064fb1954b8d4d241c974a65f83be3420cefaf`。本目录的新脚本与输出不覆盖 G3-01、G3-02、G3-06 或前两关证据。

## 实施前观测

- 指定工作树干净、detached HEAD 在上述提交。系统 `python3 -m pytest starter/tests -q` 因缺少 pytest 退出 1；在本工作树隔离 `.venv` 安装依赖后，原后端 `53 passed`。
- 原始 T01 第二轮“那 7 月呢？”和 V03 第二轮“那 6 月的时候呢？”均被当作无上文；T02 第二、三轮和 T03 第二轮未继承主体/时间。原因是 `Service._answer` 读取 `history` 后调用 `planner.plan(question)` 未传入历史。这个起点观测发生在第一次代码修改之前。

## 独立业务期望与可复验输出

运行 `.venv/bin/python docs/verification/g3-04/replay_multiturn.py` 得到 `no-key/T01.json` 等。每个文件按原题顺序逐轮保存原始请求、公开响应和完整 trace，使用实际 SQLite、真实 BM25 与知识库文件；无 Key 模式只能验证受控代码路径，不能代表真实模型语义。

| 场景 | 顺序与独立期望 |
| --- | --- |
| T01 | 6 月净营业额 156757.00；追问 7 月 162414.00；再问两月客单价 36.36/36.53，代码比较差 0.17，两个独立区间进入 `compare_periods`。 |
| T02 | 质检不合格/拒收 KB-021；停售期间推荐鸡肉poke KB-021；供应商赔付 8600 元 KB-022。每轮重新检索并引用本轮原文。 |
| T03 | 牛肉poke 现价 45 元 KB-025；6 月 18 日重新选择 KB-023，S02 当日实收 29 元。 |
| V03 | 储值现行规则满 500 赠 60 元 KB-011；6 月历史版本满 500 赠 50 元 KB-010。 |

独立运行 `.venv/bin/python -m pytest docs/verification/g3-04/test_session_context.py -q`，覆盖四组原顺序、替换门店/商品/月份、主题切换、澄清补充、拒答与异常断开旧语义、不同会话交错/API 并发、同会话等待、淘汰/重启/匿名、受控 live 工具调用。`starter/tests/conftest.py` 全局替换检索器，故原 53 项与本测试必须分进程运行。

`browser/multiturn-{1280,1440,390}.json` 保存实际浏览器逐轮请求、响应与后端 trace；同名 PNG 保存聊天视图。`frontend/tests/g3-session-context.spec.ts` 在首轮与追问之间把看板筛选改为 8 月，验证追问仍是同一会话的 7 月且请求无隐式 `context`；同时核验新对话 ID、无上文澄清、旧请求迟到不进入新会话。趋势引用仅在用户显式附加时进入聊天。刷新/服务重启后内存上下文不保证存在，欢迎页提示用户补全条件。

会话历史上限 500 个 ID、每 ID 6 轮；已执行请求的拒答及异常清空该 ID 上下文，防止后续省略主语时回退到更旧且可能不相关的主题。澄清只保留中性缺项状态。同 ID 并发采用互斥加 250 ms 有界等待，忙时返回可重试的中性状态，不修改正在执行的历史；获取锁顺序不保证 FIFO。PR #33 独立审查后的修正与复验见 [review-r1-r2/README.md](review-r1-r2/README.md)。

自然追问在规划器未改写时仍可由受控 live 模型读取前轮成功问题，并重新调用真实业务工具；澄清后的独立新题继续隔离。该增量修正的红绿证据和容量边界见 [review-r3/README.md](review-r3/README.md)。

## 固定业务提交后的付费抽样

业务提交 `4b687cc7222854deabf43de0aaa49dd6e93b0cc7`，原 T01 在同一 `session_id` 逐轮调用真实 DeepSeek `deepseek-flash`：`live/chat-1.json` 至 `chat-3.json` 含每轮 HTTP 请求/响应/trace，trace 的 `llm_calls` 含 6 次实际 API 的完整脱敏 request、response 和 usage。逐次预留与结算在 `live/ledger.json`；凭据只从共享主树 `.env.live` 只读载入，从未写入本工作树。执行器 `run_live_samples.py` 限本票 3 chat / 10 元，并在每次对外 API 前预留 2.20 元，未知 usage 保留全额。价格依据 [DeepSeek 官方价格表](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) 的 `deepseek-flash` 高峰全未缓存输入 2 元/百万 token、输出 8 元/百万 token；按最大上下文 1,048,576 和输出 4096 计算单次上界约 2.12992 元，2.20 元预留含余量。账本仅为保守估算，`billing_confirmed=false`，不等同实际账单。

3 chat 共 6 次 API，全部 HTTP 200、usage 齐全；本票估算 0.050206 元。第三关此前估算 1.167168 元，加本票为 1.217374 元；定向 chat 池由 9/18 增为 12/18。本票 chat 名额已用完，未继续调用。`.venv/bin/python docs/verification/g3-04/audit_live.py` 独立重查 SQLite 并逐轮核对账本与响应：6 月 156757.00、7 月 162414.00、两月客单价差 0.17；trace 历史轮数 0/1/2，工具分别为 `query_metrics`、`query_metrics`、`compare_periods`。T02/T03/V03 的真实模型语义仍未验证，它们目前只有上述无 Key、受控和真实检索证据。
