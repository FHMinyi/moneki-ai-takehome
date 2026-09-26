# G2-03 相关且适用的检索：执行证据

规格：[Issue #15](https://github.com/FHMinyi/moneki-ai-takehome/issues/15)。固定评审点 `4a07686449337322c87520ebca52ac838ede86db`。最终被测业务提交 **`46bbd9473818b143ffac4caeb11954b05ec0a760`**；后续提交仅整理验证脚本、证据和说明。实施与本地验证完成，等待主会话独立验收，不宣告Issue关闭。

最终 **62项G2-03检查通过**，G2-01/02 **35项通过（16+19）**，原后端 **53项通过**。未修改的全量公开评测无模型 **56/100，36/55题全绿**；检索15/15，且每题gold有正分非补位相关片段。实际35篇215片段，原文位置覆盖遗漏0字符，15问75条HTTP来源错位0。

## 复现

仓库根目录运行，复用已有 `starter/.venv`，不声称新装依赖验证。输出路径使用新名字，避免覆盖已保存原始证据。

```bash
G2_EVIDENCE=/tmp/g2-03-review-http starter/.venv/bin/python -m pytest docs/verification/g2-03/test_retrieval.py -q
G2_EVIDENCE=/tmp/g2-03-review-predecessors starter/.venv/bin/python -m pytest docs/verification/g2-01/test_ingestion.py docs/verification/g2-02/test_evidence.py -q
starter/.venv/bin/python docs/diagnostics/2026-09-27-g2-start/baseline.py --repo "$PWD" --out /tmp/g2-03-review-integration
starter/.venv/bin/python docs/verification/g2-02/audit.py /tmp/g2-03-review-integration /tmp/g2-03-review-sources.json
starter/.venv/bin/python docs/verification/g2-03/audit.py /tmp/g2-03-review-integration /tmp/g2-03-review-retrieval.json
```

`baseline.py`导出调用时HEAD并在environment.json写入精确提交，`--out`必须不存在。新测试复制当前kbqa源码到临时目录，执行公开 `python -m kbqa.rebuild` 后启动真实uvicorn/HTTP，缓存和VAR_DIR独立。子进程显式移除 `LLM_API_KEY/LLM_BASE_URL/LLM_MODEL`，health确认mock；没有读取`.env.live`、没有真实或付费模型调用。G2测试不导入starter的固定Retriever fixture；原后端53项仅作兼容回归。

## 八项验收映射

| 标准 | 命令对应检查 | 原始输出/结果 |
|---|---|---|
| 1 R01—R15正分真实相关 | `test_public_positive` 15项、`test_gold_chunk_contains_support_not_only_heading`、`audit.py`；未修改公开run_eval | `acceptance.txt`、`acceptance-http/`、`integration/eval/`、`retrieval-audit.json`：15/15；来源75/75；下表逐题内容核对，不靠零分gold |
| 2 确定性变体 | `test_variants` 10项、`test_supported_variants` 2项、`test_rewritten_chat_search_is_reproducible` 3项 | 中文无空格、Beef Poke/全角、汤面店/S01、阿里嘎多/全角S04、鲑鱼波奇饭赔付、ISO/中文/全角日期；实际KB003/013/022/029/040/061/062作期望来源 |
| 3 现行与历史边界 | `test_real_versions` 3项、`test_version_boundaries` 3项 | 真实退款6月14/15和合成6月1日版本；包含“当时”仍按日期选；status由摄取到索引一致，现行不保留旧版为有效证据 |
| 4 门店范围/过滤顺序 | `test_filter_before_topk_and_padding`、`test_incidental_store_is_not_scope`、`test_actual_store_scope_and_incidental_examples` | 两文档S01/S02夹具；真实KB020显式S03排除，KB001正文S01举例不限制S02；有适用候选不被截断漏掉 |
| 5 top_k及补位隔离 | 上述top_k=1/2/5/100；`test_unknown_and_padding_chat`、`test_tool_uses_only_eligible_evidence`、标点空查询大top_k | 返回min(top_k,total_chunks)，降序；排除项最后零分补位并明确reason/padded/evidence_eligible=false；真实chat无不适用引文，全为补位时refusal；真实Service工具输出无补位 |
| 6 同源可诊断 | `test_same_search_http_and_trace`、`test_rewritten_chat_search_is_reproducible` | 真实chat的search trace与retrieve对相同改写query的hits/scope逐项相等；trace/API含terms、expansions、候选词法分/正文焦点权重/最终分、过滤原因与适用时点 |
| 7 换材料与未知信号 | `test_replacement_alias_and_fact`、`test_shape_rerank_replacement_and_no_lexical_match`、`test_unknown_chinese_keeps_low_coverage` | 公开重建/重启后Azure Bowl→Violet Plate、17→23；Jade Trout→Amber Cod、4321→6789；旧事实无残留。英文未知或仅形状无词项零候选，中文未知保持低coverage，非空索引仍按契约补位但不认作事实 |
| 8 前序/指标不退化及红绿 | 本项pytest、前序pytest、baseline；新增最小拒答回归 | `acceptance.txt`62通过，`predecessor-final.txt`35通过，`integration/backend-tests.txt`53通过；metrics6/6、data12/12、refusal8/8，S02/S03通过；以下红绿提交完整保存 |

`evidence_eligible`表示可进入问答候选的正分且适用片段，不代表已完成答案事实证明。已有的coverage/词表信号继续保留，单轮事实选择和最终拒答质量由后续工作验收。

## 逐题正文支持核对

全部来源、完整text、词项、别名及精确分数见 `retrieval-audit.json`，可定位同一次重建后的原文位置。此表是人工阅读该输出的内容支持判断，不是产品规则。

| 题 | 相关且有效片段（节选身份） | 实际内容支持 |
|---|---|---|
| R01 | KB-013#2 | 外卖送达后24小时内的受理窗口 |
| R02 | KB-040#3 | 牛肉poke过敏原表行；同源context_spans带表头（表头不冒充连续正文） |
| R03 | KB-062#2 | Super Souper自8月15日周五周六延长至23:00 |
| R04 | KB-022#8 | 英文邮件实际CNY 8,600 credit note赔付段，不再仅SUPPLY RESUMPTION标题 |
| R05 | KB-061#1 | 小程序订单自助开票的操作和时限 |
| R06 | KB-001#9 | 净营业额为销售与负退款金额之和 |
| R07 | KB-023#3 | 当年618牛肉poke活动价及限购。该片段支持活动价，目标位于同文档其他段；未声称单片段包含全部回答事实 |
| R08 | KB-011#3 | 现行单笔500赠60规则 |
| R09 | KB-003#3 | 味噌/味增/Miso Ramen映射原表 |
| R10 | KB-029#8 | 连续两月毛利率低于35%、损耗及销量因素，不再仅议题标题 |
| R11 | KB-028#3 | 首月全门店目标900杯 |
| R12 | KB-020#1、KB-051#4 | 排烟管道/风管整改导致停火施工，停业背景真实；天数在通知后文 |
| R13 | KB-053#2（也命中KB026） | 台风当天十四点闭店的实际记录，非只用发布时刻作答案 |
| R14 | KB-027#3、KB-052#2 | 终端无法连接、网络升级切断专线与现金收款 |
| R15 | KB-014#3 | 员工7折与活动不叠加 |

## 设计与边界

- 沿用BM25。NFKC、中文相邻二元词项、英文数字整词；没有新依赖、服务或固定领域字典。别名仍从KB动态读取。tokenizer-3/loader-3使旧缓存自动失效，原文偏移、source_text、retrieval_text和context_spans映射不变。
- 适用性先于评分/截断。取代关系按新版生效日结束旧版，不依赖旧版status恰好是某个固定字符串；无日期“旧版”探索仍可跨版本，明确日期优先。门店硬限制来自声明的stores/stores_explicit，正文提及只作软线索。未新增自由文本任意适用范围的语义解析器。
- 已知别名与文字词项同权1.0；正文金额/时长/原因等形状给已有正分候选乘1.5。两者均经实际对照选择，不会给没有词项/别名命中的文档凭空造正分。复用现有focus_kinds/carries，不改回答句子选择。
- 保留每篇一条优先的多样性选取；补齐时同文档额外正分片段也标padded。适用零分先于排除项补齐，排除项固定0分、明确原因。HTTP为满足数量仍能显示这些诊断补位；问答的ranked及模型工具结果不将它们作为事实来源。
- API必需字段保持，增加padded/evidence_eligible/exclusion_reason与diagnostics。诊断含全部评分候选，适用于当前小知识库；未做大库性能承诺。
- 基于主会话对真实S03回归的裁定，Planner在scout前复用现有写操作/系统探测规则，并修SQL动词紧贴中文的边界。该补救不涉及全文拼接、正常问题内文档指令的事实选择、完整安全对抗或多轮。

## 实验、红绿与可复现快照

| 阶段 | 红灯/问题证据 | 修复/绿灯 |
|---|---|---|
| 基点、中文词项 | `86f7d02`开始保存；`d12c517`在产品修复前封存red.txt，30失败9通过；terms-*.json空格8/单字14/二元15/混合15 | `ea1d7e4`；lexical-green.txt 26通过 |
| 适用性/top-k | `99c3f29` scope-red，12失败1通过 | `a89f28e` scope-green，39通过 |
| 正文支持 | `2c7ce73` support-red，R04/R10两失败；focus-experiment.json权重1/1.5/2/3 | `eb1d1f9` support-green，41通过 |
| 全角历史日期 | `5f3efd7` extra，1失败5通过 | `8841a2e` extra-green，6通过 |
| 跨语言别名金额变体 | `f1e71f9` shape-extra，1失败2通过；alias-weight-experiment.json比较0.6/1/1.5/2 | `a4ccc7f` final.txt，50通过 |
| 最小拒答门禁 | `75908de` guard-red，7失败5通过 | `8b4d757` guard-initial，11通过/1失败（SQL边界），真实失败保留 |
| SQL边界 | guard-initial的全角SQL反例已提交 | `46bbd94` guard-final，12通过；最终acceptance，62通过 |

对照脚本不修改产品：`compare_terms.py <scheme> <out> [exported-source-root]`，另两个为`compare_focus.py <out> [exported-source-root]` / `compare_alias_weight.py <out> [exported-source-root]`。未指定源码时用当前源码；复现已保存历史对照应通过 `git archive <ref>` 导出指定快照（不必创建worktree）：词项比较用固定基点4a07686，焦点比较用a89f28e，别名权重用8841a2e。Python复用根starter/.venv，KB使用当前未改原始库。历史输出不因当前默认权重变化而覆盖。`experiment-replay.json`保存以这些历史源码快照重放三类对照的实际命令与一致结果。

`test-authoring.md`记录错误期望、别名共享词和文件名长度等真实试错；test-draft/lexical/guard-draft原始失败保留，不用它们冒充正式产品红灯。

## 全量结果与移交

最终实际代码 `46bbd94`：**56/100、36/55**。metrics6/6，retrieval15/15，data12/12，doc0/16，version0/6，hybrid6/18，multi_turn2/9，refusal8/8，safety6/9，health1/1。

首轮 `8841a2e` 的 **50/100、34/55，safety0/9** 保留于 `integration-before-alias-weight/`。检索增强让此前偶然无命中拒答的S03暴露原有安全入口缺失；本项按主会话裁定最小修复后S02/S03均通过。评测报告无metrics_unchanged失败之外，还对7种攻击的源pos.db和隔离clean.db做请求前后字节SHA256核对，全部不变；见guard-final-http及resources.json，未仅凭无写调用声称安全。

未全绿：**C01—C08、V01—V03、H01/H02/H04/H06、T01—T03、S01**。纯文档/版本回答仍有原规划路由、升序句子选择和全文拼接问题，留给G2-04；完整历史检索通过不冒充公开V03追问通过。混合、多轮及完整安全对抗留第三关。S01正常投诉问题仍走数据路径；本次没有验收文档注入攻击事实选择。没有部署/真实模型验收，也未开始G2-04。

## 自查、保护及资源

逐项比对Issue及固定点源码diff：业务仅7文件，111新增/33删除；未修改answerer/chunker、公开评分器/题库或原始输入。新增诊断与来源审计验证补位、实际引用映射和同源调用。`git diff --check`通过。自查发现的标题证据、全角时间、别名权重、拒答边界问题均保留红灯修复；最终没有已知本项合并阻塞，主会话仍需独立核验。

- checkout：`/Volumes/MACPSSD/project/moneki-ai-takehome`；分支`codex/g2-03-retrieval`，未新建worktree，未动另三个管理checkout。等待主会话明确清理，不自行合并或删除分支。
- `preservation.json`：272个原始数据/KB/公开评测/旧基线/诊断/前序证据/未提交材料哈希不变。原有未跟踪`docs/baseline/2026-09-26-followup-draft.md`、`docs/research/`原样保留。
- `resources.json`：466次自建短期服务，全部在finally退出，无常驻自建服务；每次PID、端口、隔离源码及证据路径可查。最终集成PID98083、端口60009，已退出。重复阶段共34次两库哈希检查记录，均相同。
- 保留`/tmp/moneki-g2-03-integration`、`/tmp/moneki-g2-03-final`和JSON指向的pytest/源码临时目录；未清理。仓库内证据可复核，系统之后可能回收临时目录。
- 复用运行时，无付费调用、不读取`.env.live`，无部署、未推main、未合并/关闭Issue。
