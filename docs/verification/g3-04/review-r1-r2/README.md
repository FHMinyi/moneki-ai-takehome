# PR #33 独立审查 R1/R2 修正

审查固定点 `384bef1ed1a2db0177f59f4667d89b654d72f821`。先新增断言，在该业务实现上运行得到 `red-pytest.txt`：两个澄清后独立主题用例和一个同会话无限等待用例，共 **3 failed**，随后才修改实现。原审查的详细请求/响应/trace 位于主会话保留的 `/var/folders/7v/j4gtct8n0mzg1p_8h3jscjgh0000gn/T/moneki-g304-parent-review-abs5dc6s/result.json`，本目录不覆盖它。

## 修正行为

- R1：澄清只接受符合缺项的时间片段：`7月`、`那7月份呢？`、`2026年7月`、`七月` 均能补完原来的“8号”；独立完整问题直接重新规划。实际新会话对照的“外卖退款时限？”引用 KB-013、牛肉poke 过敏原引用 KB-040，均没有旧净营业额条件；live 提示也不再带不适用的旧问句。无上文的连续省略问法继续澄清。
- R2：同一 session 在已有请求执行期间最多等待 250 ms，超时返回 HTTP 200 的结构化 `refusal` 与 `session_busy` trace，提示重试；不读取、清空或写入正在执行的会话历史。互斥锁只保证一次一个请求，不承诺 FIFO。不同 session 独立执行；忙时回复不消耗模型调用。人工持锁的 FastAPI TestClient 并发用例设 `chat_budget=1`，核验忙时响应在 0.9 秒内返回、另一会话正常查数；首请求成功时后续重试继承，首请求异常时释放锁并清除错误上下文，后续省略问题澄清。

## 复验

| 命令 | 结果与文件 |
| --- | --- |
| `.venv/bin/python -m pytest docs/verification/g3-04/test_session_context.py docs/verification/g3-04/test_live_budget.py -q` | `green-session-budget.txt`，19 passed |
| `.venv/bin/python -m pytest starter/tests -q` | `green-original-backend.txt`，53 passed，独立进程避免全局假检索器污染 |
| `.venv/bin/python -m pytest docs/verification/g3-01/test_data_chat.py docs/verification/g3-02/test_document_binding.py docs/verification/g3-06/test_trend_context.py -q` | `green-cross-ticket.txt`，70 passed |
| `G304_EVIDENCE_DIR=docs/verification/g3-04/review-r1-r2/no-key .venv/bin/python docs/verification/g3-04/replay_multiturn.py` | `green-replay.txt`，T01/T02/T03/V03 原题每轮完整请求/响应/trace 均保存于 `no-key/` |
| `BROWSER_BASE_URL=http://127.0.0.1:8764 G304_EVIDENCE_DIR=../docs/verification/g3-04/review-r1-r2/browser npx playwright test tests/g3-session-context.spec.ts --workers=1` | `green-browser.txt`，1280/1440/390 及迟到响应共 4 passed；新目录保存逐轮 JSON/截图 |
| `npm run build` | 构建成功；详见本次执行记录 |

`http-topics.json` 另保存实际 `127.0.0.1:8764` HTTP 的三组两轮请求、响应和后端 trace：两组切换主题均得到本轮文档，月份自然变体继续原查数问题。

此前 `live/chat-{1,2,3}.json` 是真实模型原 T01 在业务提交 `4b687cc` 上的样本，不能当作本轮修正后的真实模型验证。本轮未新增任何付费请求，账本保持 3 chat、6 API、估算人民币 0.050206 元（非账单）。
