# 评测报告

- 服务地址：`http://127.0.0.1:8015`
- 题库：`/private/tmp/moneki-g1-05-4r7gvnd1/source/eval/public_questions.jsonl`
- 生成时间：2026-09-27 02:00:54
- 知识库：载入 35 份文档（用于 quote 逐字校验）

## 总分

**6.00 / 6.00（100.0%）**，6 题全绿 / 共 6 题。

每题耗时：中位数 0.00 秒，最大 0.00 秒，合计 0.0 秒。

## 分类别

| 类别 | 得分 | 满分 | 比例 | 全绿题数 |
|---|---|---|---|---|
| 指标接口（`metrics`） | 6.00 | 6.00 | 100.0% | 6 / 6 |

## `/api/health` 快照

```json
{
  "status": "ok",
  "llm_mode": "mock",
  "kb_docs": 36,
  "kb_chunks": 72,
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
  "index_key": "8651fac326e2",
  "kb_warnings": [
    "跳过没有 KB 编号的文件：README.md"
  ]
}
```

## 没通过的题（0 道）

没有。

## 全部题目

| 题号 | 类别 | 得分 | 满分 | 耗时（秒） |
|---|---|---|---|---|
| M01 | metrics | 1.00 | 1.00 | 0.00 |
| M02 | metrics | 1.00 | 1.00 | 0.00 |
| M03 | metrics | 1.00 | 1.00 | 0.00 |
| M04 | metrics | 1.00 | 1.00 | 0.00 |
| M05 | metrics | 1.00 | 1.00 | 0.00 |
| M06 | metrics | 1.00 | 1.00 | 0.00 |
