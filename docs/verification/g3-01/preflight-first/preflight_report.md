# 大模型接入预检报告

生成时间：2026-09-27T12:55:36.628+08:00。
被测服务：http://127.0.0.1:8033。
假模型地址：http://127.0.0.1:9033/ds-gw。
注入的模型名：preflight-model-7f3a。
工具版本：llm_gateway.py 2.0.0。
总体结论：**未通过**，14 项检查里有 1 项失败（P1）。
有 9 项因为没有素材而未检查（P2、P3、P4、P5、P6、P7、P10、P13、P14），请看下面的逐项说明确认这是不是你想要的。

## 检查结果一览

| 编号 | 检查项 | 结果 | 说明 |
|---|---|---|---|
| P1 | 服务确实把请求发到了注入的 LLM_BASE_URL（含路径前缀） | 失败 | 假模型一次请求都没收到：服务没有按注入的 LLM_BASE_URL 发请求，或者还停在 mock 模式，或者没有用新环境变量重启。 |
| P2 | 请求里的 model 等于注入的 LLM_MODEL | 未检查 | 假模型一次请求都没收到，本项没有素材可查，先看 P1。 |
| P3 | 注入的 Key 以 Authorization: Bearer 发送 | 未检查 | 假模型一次请求都没收到，本项没有素材可查，先看 P1。 |
| P4 | 只用了 DeepSeek 文档列出的顶层参数 | 未检查 | 假模型一次请求都没收到，本项没有素材可查，先看 P1。 |
| P5 | max_tokens 不设，或不小于 2048 | 未检查 | 假模型一次请求都没收到，本项没有素材可查，先看 P1。 |
| P6 | 没有访问 {prefix}/chat/completions 之外的任何路径 | 未检查 | 假模型一次请求都没收到，本项没有素材可查，先看 P1。 |
| P7 | 工具定义规范，且每一个工具调用都以 role=tool + tool_call_id 回传 | 未检查 | 假模型一次请求都没收到，本项没有素材可查，先看 P1。 |
| P8 | 每个场景下 /api/chat 都返回 HTTP 200 与字段完整的合法 JSON | 通过 | 32 次问答全部返回 200 和字段完整的 JSON。 |
| P9 | 模型不可用时给出结构化 refusal，answer 从不是空串 | 通过 | 模型不可用的场景下都给了结构化 refusal 或有据可查的回答，answer 从不是空串。 |
| P10 | 思考内容没有漏进 answer / citations / data_evidence | 未检查 | 假模型一次都没能把带标记的思考内容发出去（请求没到、或者都被挡下了），本项无从检查，先看 P1 和 P8。 |
| P11 | /api/chat 在时限内返回（含长时间无响应的场景） | 通过 | 最慢的一次是 0.06 秒，都在 180 秒以内。 |
| P12 | 注入环境变量后 /api/health 报告 llm_mode = live | 通过 | llm_mode = live。 |
| P13 | 多轮工具调用之间 reasoning_content 原样回传（没有触发 400） | 未检查 | 假模型一次请求都没收到，本项没有素材可查，先看 P1。 |
| P14 | 保持连接的空行与 SSE 注释没有把服务弄坏 | 未检查 | normal 场景本身就没有拿到回答，无法判断保持连接是不是额外的问题，先修前面的检查。 |

## 逐项证据

### P1 服务确实把请求发到了注入的 LLM_BASE_URL（含路径前缀）

结果：失败。
说明：假模型一次请求都没收到：服务没有按注入的 LLM_BASE_URL 发请求，或者还停在 mock 模式，或者没有用新环境变量重启。

```json
{
  "expected_base_url": "http://127.0.0.1:9033/ds-gw",
  "expected_path": "/ds-gw/chat/completions",
  "chat_completions_requests": 0,
  "per_scenario": {
    "normal": 0,
    "thinking_starved": 0,
    "empty_content": 0,
    "json_empty": 0,
    "bad_tool_args": 0,
    "content_filter": 0,
    "insufficient_resource": 0,
    "aborted": 0,
    "http_401": 0,
    "http_402": 0,
    "http_422": 0,
    "http_429": 0,
    "http_500": 0,
    "http_503": 0,
    "slow": 0,
    "hang": 0
  }
}
```

### P2 请求里的 model 等于注入的 LLM_MODEL

结果：未检查。
说明：假模型一次请求都没收到，本项没有素材可查，先看 P1。

### P3 注入的 Key 以 Authorization: Bearer 发送

结果：未检查。
说明：假模型一次请求都没收到，本项没有素材可查，先看 P1。

### P4 只用了 DeepSeek 文档列出的顶层参数

结果：未检查。
说明：假模型一次请求都没收到，本项没有素材可查，先看 P1。

### P5 max_tokens 不设，或不小于 2048

结果：未检查。
说明：假模型一次请求都没收到，本项没有素材可查，先看 P1。

### P6 没有访问 {prefix}/chat/completions 之外的任何路径

结果：未检查。
说明：假模型一次请求都没收到，本项没有素材可查，先看 P1。

### P7 工具定义规范，且每一个工具调用都以 role=tool + tool_call_id 回传

结果：未检查。
说明：假模型一次请求都没收到，本项没有素材可查，先看 P1。

### P8 每个场景下 /api/chat 都返回 HTTP 200 与字段完整的合法 JSON

结果：通过。
说明：32 次问答全部返回 200 和字段完整的 JSON。

```json
{
  "attempts": 32,
  "failures": []
}
```

### P9 模型不可用时给出结构化 refusal，answer 从不是空串

结果：通过。
说明：模型不可用的场景下都给了结构化 refusal 或有据可查的回答，answer 从不是空串。

```json
{
  "failing_scenarios": [
    "aborted",
    "bad_tool_args",
    "content_filter",
    "empty_content",
    "hang",
    "http_401",
    "http_402",
    "http_422",
    "http_429",
    "http_500",
    "http_503",
    "insufficient_resource"
  ],
  "checked": 24,
  "skipped_invalid_responses": 0,
  "failure_marker": "FAILOUT-91a150c04b91",
  "declared_tools": [],
  "problems": []
}
```

### P10 思考内容没有漏进 answer / citations / data_evidence

结果：未检查。
说明：假模型一次都没能把带标记的思考内容发出去（请求没到、或者都被挡下了），本项无从检查，先看 P1 和 P8。

```json
{
  "marker": "RSN-12c9ae4c1b31",
  "inspected_answers": 32,
  "responses_carrying_the_marker": 0,
  "requests_with_thinking_disabled": 0,
  "leaks": []
}
```

### P11 /api/chat 在时限内返回（含长时间无响应的场景）

结果：通过。
说明：最慢的一次是 0.06 秒，都在 180 秒以内。

```json
{
  "limit_seconds": 180.0,
  "timed_attempts": 32,
  "slowest": [
    {
      "scenario": "normal",
      "seconds": 0.06
    },
    {
      "scenario": "normal",
      "seconds": 0.02
    },
    {
      "scenario": "thinking_starved",
      "seconds": 0.02
    },
    {
      "scenario": "thinking_starved",
      "seconds": 0.02
    },
    {
      "scenario": "empty_content",
      "seconds": 0.02
    }
  ],
  "offenders": [],
  "unreachable_attempts": []
}
```

### P12 注入环境变量后 /api/health 报告 llm_mode = live

结果：通过。
说明：llm_mode = live。

```json
{
  "status": 200,
  "error": null,
  "body": {
    "status": "ok",
    "llm_mode": "live",
    "kb_docs": 35,
    "kb_chunks": 215,
    "valid_sales_rows": 18290,
    "today": "2026-09-01",
    "data_period": {
      "start": "2026-05-01",
      "end": "2026-08-31"
    },
    "cleaning_report": {
      "raw_rows": 18628,
      "removed": {
        "1_unparseable_date": 8,
        "2_empty_amount": 150,
        "3_qty_le_zero": 30,
        "4_store_not_in_stores": 10,
        "5_product_not_in_products": 40,
        "6_duplicate_row": 100
      },
      "removed_rows": 338,
      "kept_rows": 18290,
      "kept_sales_rows": 18196,
      "kept_refund_rows": 94
    },
    "index_key": "c2fac231ae26",
    "kb_warnings": [
      "跳过没有 KB 编号的文件：README.md",
      "使用 GBK 解码：KB-062_旧OA导出_营业时间调整通知.txt"
    ]
  }
}
```

### P13 多轮工具调用之间 reasoning_content 原样回传（没有触发 400）

结果：未检查。
说明：假模型一次请求都没收到，本项没有素材可查，先看 P1。

### P14 保持连接的空行与 SSE 注释没有把服务弄坏

结果：未检查。
说明：normal 场景本身就没有拿到回答，无法判断保持连接是不是额外的问题，先修前面的检查。

```json
{
  "normal_answered": false,
  "slow_answered": false,
  "slow_statuses": [
    200,
    200
  ],
  "slow_answer_types": [
    "refusal",
    "refusal"
  ]
}
```

## 各场景明细

| 场景 | 问题 | HTTP | 耗时（秒） | answer_type | answer 摘要 | 模型请求数 |
|---|---|---|---|---|---|---|
| normal | 你们的退款规则是怎么规定的？ | 200 | 0.06 | refusal | 抱歉，我暂时无法回答。 | 0 |
| normal | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| thinking_starved | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| thinking_starved | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| empty_content | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| empty_content | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| json_empty | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| json_empty | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| bad_tool_args | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| bad_tool_args | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| content_filter | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| content_filter | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| insufficient_resource | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| insufficient_resource | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| aborted | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| aborted | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_401 | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_401 | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_402 | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_402 | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_422 | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_422 | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_429 | 你们的退款规则是怎么规定的？ | 200 | 0.01 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_429 | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_500 | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_500 | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_503 | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| http_503 | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| slow | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| slow | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| hang | 你们的退款规则是怎么规定的？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |
| hang | 最近一段时间的整体经营情况怎么样？ | 200 | 0.02 | refusal | 抱歉，我暂时无法回答。 | 0 |

## 场景说明

normal：模型一切正常；带 tools 时先返回两个工具调用，再返回一个，最后才给正文。
thinking_starved：只有当你把 max_tokens 设得小于 1024 时才会咬人，此时正文为空、finish_reason 为 length。
empty_content：没有 tool_calls 而正文是空串，finish_reason 仍然是 stop，这种要按错误处理。
json_empty：只有当你用了 response_format=json_object 时才会咬人，文档说 JSON 模式偶尔会返回空内容。
bad_tool_args：工具调用的 arguments 是被截断的非法 JSON，必须处理解析失败。
content_filter：finish_reason 为 content_filter，正文是半截话、不是空串。
insufficient_resource：finish_reason 为 insufficient_system_resource，正文为空。
aborted：finish_reason 为 aborted，正文写到一半被掐断、不是空串，只看正文空不空的实现会漏掉它。
http_401：HTTP 401 认证失败。
http_402：HTTP 402 余额不足。
http_422：HTTP 422 参数错误。
http_429：HTTP 429 限速。
http_500：HTTP 500 服务器错误。
http_503：HTTP 503 服务器繁忙。
slow：服务繁忙时的保持连接：非流式在正文前发空行，流式发 `: keep-alive` 注释。
hang：收下连接却一直不回，你的单次模型调用必须有超时。

## 注意

本机没有 DeepSeek Key，假模型的全部行为都来自官方文档，没有对照过真实接口。
不回传 reasoning_content 时的 400、response_format 取值不合法时的 422，都是按文档推定的。
P5 的 max_tokens ≥ 2048 和 P11 的 180 秒总预算是这份作业的规定，不是 DeepSeek 服务端的限制。
走 OpenAI 兼容路线的，请把这份报告贴进 `LLM_SETUP.md` 第 7 节（自测结果）。
