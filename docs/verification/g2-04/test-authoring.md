历史退款测试最初误填 2 小时，实际 KB-012 原文为 7 天。extra-red 原始输出保留，其中该项不是产品缺陷；修正期望后重跑。取证异常注入随方法重构由 _doc_block 改为 _document_evidence，并增加目标字符串存在断言；evidence-attempt 中对应失败是注入未触发，不是产品异常未处理。

74583d2 的 Agent-Decision 误写16个失败，实际 evidence-red 为15失败1通过（16项）。以原始输出为准。

quote-limit-red 命名虽含red，实际首探针通过：它因问题欠限定、检索分低而拒答，遮住引用长度缺陷。quote-limit-confirmed-red 加入明确“规定”语境后真正复现NFKC规范化428字符。两者原输出均保留。

`test_unretrieved_fact_not_borrowed` 的最初注释误称命中是订金，实际夹具只有配送主题和会员开卡手续费。真实trace显示该手续费本身被检出，最后因证据弱而不作答；这个测试只证明弱相关不回答，不能声称它单独证明“未检出片段隔离”。有效片段隔离由 `_document_evidence` 的原文范围、每次quote逐字检查和独立audit的非补位身份核对共同验证。

最终资源摘要刷新曾尝试再次读取已被pytest自动回收的旧server.log并报FileNotFoundError；该日志此前已复制到验证目录，改用已保存副本并以.log.txt提交（.log受gitignore忽略）。资源摘要从已保存HTTP记录重新生成，不依赖临时路径仍存在。
