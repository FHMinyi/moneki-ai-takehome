# PR31 R1/R2 审查增量证据

实际审查固定点 `94e21e3`；红灯 `d44b4e0`；R2独立修复 `b6299b5`；R1与控制器迁移固定 `eb7cad45a2a5c1792111eb24763a0bf2e84e6dc0`。本轮没有新增真实模型调用，票内仍7chat/25实际API、估算1.089330元，旧chat4—7与账本均保持原字节。

当前实现与免费回归交主会话独立复核，不能据受控通过宣称新协议已真实模型验证或通用语义蕴含证明。

## R1：来源真实与支持所问事实分开

原实现四个真实检索误引均复现：外卖时限→堂食当场条款；外卖身份证件→员工工牌；迟到申诉时限→15分钟迟到记次；外卖时限→会员储值30天。主会话与spec审查原始快照在parent-open-*.json/spec-open-probes.json。九项初始失败包括这四项及R2五项，见red.txt/red-test-source.py。

新协议在同一次facts选择中记录`binding.subject/attribute/value`，不是新增模型判断阶段：

- question锚点须来自原问题；来源text须在所选quote或实际context中出现。代码计算正文offset，不能提供另一个文档或任意source。
- 主体可绑定实际metadata.title，以`source_field=metadata.title`、offset=null标注，不能把文件标题伪称正文位置。
- 复用已有别名表的mentions/strict_mentions、FOCUS_WORDS/carries与封闭问句检查。实际主体不一致、明确前后限定词冲突、属性/值型不符、关键邻接限定语被省略、跨无关句子拼锚点、只给布尔支持字段会拒绝交付。
- 支持属性解释仍由本次模型作出。疑问词与陈述语、英汉译义不是同词，trace分别标literal/kb_alias/value_shape/translation；这些标签不等于确定性语义证明。代码不新增通用同义词词表、不套整个mock回答器。

### 几种门槛的实际对照

| 方案 | 正例 | 误引/不足 | 结论 |
|---|---|---|---|
| 94e21e3真实ID+弱词重叠 | 正常题可答 | 四审查负例均被误交付 | 不合格，原审查原始证据保留 |
| 工作中锚点+全句残余字面覆盖 | 简单“外卖订单多久内可以退款”可答 | 可拒四负例，却把正常C01“申请”/来源“提出”误拒 | 已撤回；conservative-limits.json保留这对相同事实问法，不降低验收 |
| eb7cad4同次锚点+可定位冲突 | C01—C08/V01/V02全体、普通退款改写、别名和独立材料均可答 | 四负例带完整binding仍拒绝；省略申诉、跨句拼接、外送/自取同量纲数字偷换被拒 | 当前交审方案；仍有限语义范围，不称数学蕴含证明 |

原正例不是仅更换schema后看状态：`test_public_bound_http`逐项核对真实quote/offset和文档回答，仍使用原问题。四原负例在新测试里提供完整subject/attribute/value及真实引用ID，不靠缺少新字段拒答；另有相同数字类型但故意只锚定共同词头“订单”的外送/自取替换例，检查实际主体前置限定冲突。

独立KB使用全新编号/名称/别名、37→83分钟与HTTP43→89分钟，MD/TXT/GBK/HTML每次真实重建后重启再问；测试期望不由生产代码生成。没有生产题号、文档ID或申请/提出特判映射。

## R2：依据不足状态不传递政策断言

规范输出为`{"answer_type":"refusal","reason":"insufficient_evidence"}`。代码中性渲染“本次没有足够可核对的依据……无法确定”，没有自由政策陈述字段。旧`refusal + answer`只兼容其拒答状态，整段说明均不交给用户；原始模型内容保留在已脱敏trace。不是按KB编号特判，也不是仅删除数字。要展示政策概括仍须doc证据绑定。

无检索时“外卖退款不需要身份证”“所有门店扣手续费”等句子不再透出。真实tool error单独记tool_failure，网络/模型错误沿原异常链处理，不把异常或上限机械说成资料不存在。

完整chat7四轮已保存的真实模型响应通过本地HTTP回放，实际Service重新执行同样检索：现在可安全呈现依据不足，不再因v2/KB-013造成data_binding技术错误，也不转述无引用的政策摘要。`chat7-free-replay.json`是b6299b5独立记录，`final-replay/chat7-free-replay.json`为eb7cad4后的固定复查；两者都明确是免费回放，不能称新的真实模型理解验证。

## 固定eb7cad4的命令与结果

```bash
G302_HTTP_OUT="$PWD/docs/verification/g3-02/review-r1-r2/final-unit-http" \
G302_REVIEW_OUT="$PWD/docs/verification/g3-02/review-r1-r2/final-replay" \
starter/.venv/bin/python -m pytest \
  docs/verification/g3-02/test_document_binding.py \
  docs/verification/g3-02/review-r1-r2/test_anchored_selection.py \
  docs/verification/g3-02/review-r1-r2/test_review.py \
  docs/verification/g3-01/test_credentials.py \
  docs/verification/g3-01/test_data_chat.py starter/tests -q
# fixed-backend.txt：169 passed

G302_HTTP_OUT="$PWD/docs/verification/g3-02/review-r1-r2/final-http" \
starter/.venv/bin/python -m pytest docs/verification/g3-02/test_http.py \
  docs/verification/g3-02/review-r1-r2/test_bound_http.py -q
# fixed-http.txt：49 passed
```

复跑必须换新的输出目录，不覆盖上述证据。后端169项为83原后端/凭证/查数、39既有文档/轮数协议、33锚点/变体/替换、14审查回归（包含R2完整回放）。HTTP49项为30既有场景迁移和19新增正反/替换，包含6轮工具+最终none、违约工具不执行、原生异常、重建与注入。控制器注释只存在验证目录，生产代码不导入它。

浏览器`browser.txt`4PASS，真实HTTP控制器下1280/1440/390核对新绑定返回的正文与支持性标题引用，逐条核对每个引用而非仅一个元素；未知字段兼容仍通过。390截图已目视检查。前端产品代码未改变，仅测试适应多条真实引用。此前20看板和199原RAG结果保留；本增量未修改mock取证逻辑、检索或前端产品，不声称重新运行了这些无影响的大套件。

## 保留、过程失误与资源

`preserved-review-and-live.json`核对chat1—7、账本、独立R2回放均与b6299b5字节相同；`protection.txt`继续核对3186固定起点tracked材料0差异、前票3065哈希一致+1用户移除草稿例外、research两文件一致。

开发时再次运行R2测试曾覆盖本票新提交的回放文件，已先另存`chat7-free-replay-r1-working.json`，再从b6299b5逐字恢复。测试现默认新临时目录，指定输出存在则拒绝覆盖；原付费样本和原失败未改。初始锚点测试两处选择器取错句子/不存在source锚点、过严门槛、值型把“几小时”误当封闭问题的既有解析问题及修复前输出均留存。最终通过不抹去这些失败。

R2另小修verify_no_key.py传播子进程失败退出码。新增模型阶段、额外付费、合并、关Issue、部署和清理均未执行。资源增量见resources.json；保留旧两组服务以及本次harness43061/model51913/API43065:51914供独立验证，等待明确清理指令。旧共享venv/node_modules/cache/var和G306独立工作树均不动。
