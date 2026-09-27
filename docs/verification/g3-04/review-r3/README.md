# PR #33 自然追问受控 live 修正

固定点 `b8b7433a601d9f2da5e47966ae942543fad803ea` 的主会话负例保存在 `parent-negative.json`：同一会话先问“S02 6月牛肉poke销量是多少？”，再问“能按天展开看看吗？”，规划器未改写第二问，live 执行入口收到空历史，无法知道前轮真实日期、门店和商品。先新增受控 live 测试在旧实现运行，`red-natural-followup.txt` 为 **1 failed**，随后才修改实现。

修复区分上一轮状态：已成功回答的会话即使未触发规则式追问改写，仍向模型提供最近 3 条旧问题/解析问句供理解指代；旧答案和旧证据不进入提示。上一轮为澄清且本轮未补其缺项时，模型历史重置。本轮明确给出的新主题、门店、商品、时间或指标优先，工具仍须本轮重新执行。trace 新增 `model_context` 记录模型实际收到的历史轮数与澄清重置标记。

`controlled-live-natural.json` 是零付费、真实 SQLite 业务工具与受控模型的两轮完整请求、响应和 trace。模型第二轮实际收到“S02 6月牛肉poke销量是多少？”，调用 `daily_metrics(start=2026-06-01,end=2026-06-30,store_id=S02,product_id=P06)`；结果与独立 SQLite 调用逐字段相同。整月逐日结果超过当前回答容量，因此受控模型最终给出中性缩小日期范围澄清；此证据证明上下文送达和本轮重新查数，不冒称已完成整月逐日展示或真实模型语义验证。R1 的澄清后独立退款/过敏原问题仍向执行入口传空历史，并与独立新会话回答一致。

| 验证 | 结果 |
| --- | --- |
| `G304_NATURAL_EVIDENCE_DIR=docs/verification/g3-04/review-r3 .venv/bin/python -m pytest docs/verification/g3-04/test_session_context.py -q -k live_natural_followup_keeps_successful_question_and_requeries` | `green-controlled-natural.txt`，1 passed |
| `.venv/bin/python -m pytest docs/verification/g3-04/test_session_context.py docs/verification/g3-04/test_live_budget.py -q` | `green-session-budget.txt`，20 passed |
| `.venv/bin/python -m pytest starter/tests -q` | `green-original-backend.txt`，53 passed，独立进程 |
| `.venv/bin/python -m pytest docs/verification/g3-01/test_data_chat.py docs/verification/g3-02/test_document_binding.py docs/verification/g3-06/test_trend_context.py -q` | `green-cross-ticket.txt`，70 passed |
| `G304_EVIDENCE_DIR=docs/verification/g3-04/review-r3/no-key .venv/bin/python docs/verification/g3-04/replay_multiturn.py` | `green-replay.txt`，原T01/T02/T03/V03顺序与完整逐轮证据 |
| `BROWSER_BASE_URL=http://127.0.0.1:8764 G304_EVIDENCE_DIR=../docs/verification/g3-04/review-r3/browser npx playwright test tests/g3-session-context.spec.ts --workers=1` | `green-browser.txt`，1280/1440/390及迟到响应4 passed |

本轮没有新增真实模型 API 请求。原 `live/chat-{1,2,3}.json` 仍只属于旧业务提交 `4b687cc` 的原 T01 真实样本；当前修正的自然追问只由受控模型和真实业务工具验证。
