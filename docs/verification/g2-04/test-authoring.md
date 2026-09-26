历史退款测试最初误填 2 小时，实际 KB-012 原文为 7 天。extra-red 原始输出保留，其中该项不是产品缺陷；修正期望后重跑。取证异常注入随方法重构由 _doc_block 改为 _document_evidence，并增加目标字符串存在断言；evidence-attempt 中对应失败是注入未触发，不是产品异常未处理。

74583d2 的 Agent-Decision 误写16个失败，实际 evidence-red 为15失败1通过（16项）。以原始输出为准。
