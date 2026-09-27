# S01 最终 JSON 围栏兼容（免费验证）

基线 `994765815f71342d2a3505fb20d5abe3e825b115`，产品提交 `674dd9f`。原真实模型 trace 位于 `../g3-05/optional-5b6a4ca/eval-live/chat-trace.jsonl` 的 chat 37；最终输出是完整单层 ```json 围栏，内部为合法 doc/facts 对象，选择真实 KB-060“出餐慢12条”证据。旧 finalise 直接 json.loads，语法失败后误报 answer_type。

修复只在最终解析边界接受完整单层 json/无语言围栏；不截取夹杂文字，不接受多围栏或嵌套围栏。JSON 语法错误与非对象顶层用 answer_json 准确报告；规范化的 content 同时传给文档和数据渲染，既有字段和来源校验保持。初始统一提示要求仅输出一个 JSON 对象、不带围栏或前后文。trace 的原模型响应不改。

- red.txt：改动前 6 failed / 10 passed，包含原 S01、两种围栏、data 下游和错误分类红灯。
- green.txt：16 项本次定向 + 11 项原 rescue，共 27 passed。负例含坏 JSON、混杂文本、多围栏、其他语言围栏、非对象、多个 JSON、伪证据和额外字段。
- regression.txt：现有文档选择、来源与数据引用等受影响回归；不执行长连接时限测试。
- answer.json：原 S01 原响应免费重放后的实际答案与引用。原 KB 源文及全部 context offsets 在加载时逐条验证。

复现命令（make setup 环境）：

```sh
PYTHONPATH=starter starter/.venv/bin/python -m pytest docs/verification/g3-json-envelope/test_envelope.py docs/verification/g3-optional-rescue/test_rescue.py -q
```

本次实际复用 `/tmp/moneki-g305-fresh-4591fab/starter/.venv/bin/python`，PYTHONPATH 指向本工作树 starter。没有付费调用，没有重跑55题；原94/53报告、模型响应和原始记录未修改，不声称新分数或模型稳定性。没有新增常驻服务。
