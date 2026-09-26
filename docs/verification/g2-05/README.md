# G2-05 checkpoint：知识库替换暴露第二关阻塞

**未完成验收，不创建最终PR。** 主会话在收到最小复现后确认退回原G2-04修复，并要求先提交本诊断checkpoint、交出共享工作区。这里所有应用结果仅属于 **358859a5be641b04395f314029e4b9325631dd8a**，不能作为未来修复提交的验收证据。

## 已确认阻塞与最小复现

无标题文档的第一行真实正文被隐式标题身份吞掉。KB-970.md是独立手写别名表：

```markdown
| 标准写法 | alias |
|---|---|
| 翡翠饭 | Ivory Bowl |
```

KB-971.md仅包含 `翡翠饭的配送时限为31分钟。`。公开重建并重启后：

| 问题/条件 | retrieve | chat |
|---|---|---|
| 无标题，翡翠饭的配送时限是多少分钟？ | 正分、非补位、KB-971连续原文 | refusal、无引用，失败 |
| 无标题，Ivory Bowl的配送时限是多少分钟？ | 正分首位10.2566、eligible=true、别名展开正确 | refusal、evidence.candidates=[]，失败 |
| 仅加独立标题 `# 配送规范`，同样中文问题 | 正分同源原文 | doc、31分钟、连续引用，通过 |
| 仅加独立标题，同样英文别名问题 | 正分同源原文 | doc、31分钟、连续引用，通过 |

[reproduce_heading.py](reproduce_heading.py)保留本项预期；当前基点执行会退出1，不能改成通过。[heading-repro/http.json](heading-repro/http.json)记录四次完整HTTP/trace及两次公开重建/服务退出；[inputs](heading-repro/inputs/)保存两组实际文件字节。期望31分钟直接来自手写夹具，未调用生产函数制造答案。

读码定位（对应358859a）：`loader.py:204-209,252`无明确标题时取第一行；`chunker.py:90`把document.title加入heading；`units.py:117-119,148-152`将与heading相同的句子标为heading；`docfacts.py:200`排除heading。A/B支持这一条链，但本项不修改业务。最初怀疑别名取证；中文全称同样失败、加标题两种问法都通过，排除了“只因别名解析失败”的解释。

扩展生命周期实际运行见[kb-lifecycle/http.json](kb-lifecycle/http.json)，输入逐阶段保存在[input-snapshots](kb-lifecycle/input-snapshots/)。初始MD31分钟、新增HTML19小时、修改为GBK TXT47分钟并换别名、删HTML、换目录为GBK TXT29小时：**5阶段中4失败1通过**。失败均为新事实已进入retrieve、chat无依据拒答；删除阶段旧事实淘汰并拒答通过。每阶段首条失败即停止该阶段剩余问句，因此旧别名拒答和切库后的第二条旧别名检查尚未执行，不能声称全部生命周期已验收。`result.json`明确passed=false。后续必须在修复提交重跑整套，不允许给所有夹具补标题以掩盖产品缺陷。

## 当前九项门槛状态

| # | 状态（仅旧基点358859a） | 实际证据 |
|---|---|---|
| 1 干净源码安装及三步 | 已通过 | clean-delivery/preflight.json、setup.txt、commands.json；git archive，无venv/node_modules/dist/var/cache/env；全新venv和npm ci |
| 2 未改55题全量 | 已通过指定门槛 | integration/eval/report.json、report.md：88.5/100、49/55；metrics6/6、data12/12、retrieval15/15、doc16/16、V01/V02、health全过 |
| 3 独立历史问句 | 已通过 | 179项包含5条test_history_boundary；integration/rag-http对应HTTP。V03追问仍失败，不把单轮补充当整题 |
| 4 KB增删改换库/格式/别名及chat | **阻塞** | 上述无标题正文缺陷；保留真实失败与输入，不降断言 |
| 5 原有及新增真实RAG/十类诊断 | 前序回归通过；新缺陷待修 | 179 passed（16+19+62+82）；原后端53；旧诊断16 passed/3 failed，3项仅为overlap拼接断言；完整性用G2-02偏移覆盖另证，见下表 |
| 6 第一关看板/数据保护 | 已通过 | 原始浏览器26、替换3、空3；原始/替换/空数据API与截图。2153个保护文件未变，2223导出文件字节与固定提交相同 |
| 7 EVAL_REPORT并列最终阶段 | 待完成 | 旧原始mock17/live25.5/G2起点41保留；本次88.5只在本checkpoint保存，修复后重新全量及更新根报告 |
| 8 DEBUG_LOG/AI_USAGE/README最终说明 | 待完成 | 本checkpoint记录实际新问题与脚本错误，不提前宣告最终交付；根报告暂不改 |
| 9 剩余问题移交 | 阻塞已报主会话 | 无标题正文为第二关共享证据问题，交回G2-04；其余已验证失败与代码风险分列下文 |

十类启动诊断行为映射（新环境真实执行，旧诊断不改写）：

| 缺陷 | 当前行为证据 |
|---|---|
| D01 格式遗漏 | test_original_identity_and_formats、test_format_through_rebuild_http；实际35篇 |
| D02 GBK | test_actual_gbk_exact_text、test_invalid_encoding_never_silently_drops_bytes |
| D03 HTML | test_actual_html_visible_text、test_html_paragraphs_and_entities |
| D04 丢尾 | test_boundary_full_coverage的10种长度、test_actual_corpus_coverage及g2-02-audit.json：35篇215块，遗漏0字符；旧301/600/601直接拼接因overlap重复仍失败，不删旧输出 |
| D05 中文 | 15条test_public_positive、变体/实际相关内容审计；g2-03-audit.json |
| D06 来源 | test_duplicate_rerank_padding_identity_http、75条真实HTTP来源审计错位0 |
| D07 版本 | test_real_versions/test_version_boundaries + 5条完整历史问句 |
| D08 top-k前过滤 | test_filter_before_topk_and_padding及补位不可引用回归 |
| D09 重建/换库 | 前序生命周期/别名/缓存迁移通过；本项chat新增缺陷独立列阻塞，不能拿缓存成功掩盖 |
| D10 真实计数 | test_empty_and_non_document_health、全量health35篇215块 |

实施中新发现的回归也在179项里真实运行：空白块/局部标题、表格上下文、S03最小拒答门禁、H05数据原因路径、属性同主体同分句、普通/省略/否定问法、开放“什么”、NFKC长度、异常trace。两项异常注入仅证明错误诊断，不冒充真实RAG。原后端53项包含既有固定检索fixture，仅作为兼容检查。

## 环境、命令及源码边界

macOS26.7 arm64、Python3.12.14、Node24.19.0、npm12.0.2、GNU Make3.81。仅在此平台实测。完整环境见clean-delivery/environment.json，依赖实装版本见python-dependencies.txt。复用pip/npm/Chromium下载缓存，**没有复制已安装环境**。未读取.env.live、未调用模型；清除LLM三变量及DATA_DIR/KB_DIR/VAR_DIR/TODAY，服务health为mock，today默认2026-09-01。

本次实际入口（从主checkout运行）：

```bash
python3.12 docs/verification/g1-05/verify_delivery.py --commit 358859a5be641b04395f314029e4b9325631dd8a
python3.12 docs/verification/g2-05/verify_rag.py --work /tmp/moneki-g1-05-u99qwxp5 --out /tmp/moneki-g2-05-rag-01
PYTHONDONTWRITEBYTECODE=1 /tmp/moneki-g1-05-u99qwxp5/source/starter/.venv/bin/python docs/verification/g2-05/verify_kb.py --source /tmp/moneki-g1-05-u99qwxp5/source --out /tmp/moneki-g2-05-kb-02
PYTHONDONTWRITEBYTECODE=1 /tmp/moneki-g1-05-u99qwxp5/source/starter/.venv/bin/python docs/verification/g2-05/reproduce_heading.py --source /tmp/moneki-g1-05-u99qwxp5/source --out /tmp/moneki-g2-05-heading-final
```

输出目录须新建且不存在。G1脚本实际完整执行make setup/rebuild/run、53后端、typecheck、metrics、三套浏览器和两套替换API；随后verify_rag重新make rebuild恢复原输入，使用同一新安装的Python与导出源码再make run全量55题。精确子命令、cwd、变量、退出码见clean-delivery/commands.json与integration/commands.json、continuation-commands.json；runner-logs保留顶层输出。

所有应用源码来自固定git archive。G1浏览器额外注入delivery.spec.ts，SHA-256由clean-delivery/tested-tree.json记录。G2脚本在导出外运行、复制的应用模块来自导出；验证脚本哈希见tested-tree-final.json。历史迁移测试所需两个旧模块从固定8b72f47导出为只读history-fixture，版本/哈希/测试唯一覆盖内容见integration/verification-overlays.json。只替换测试的git show读取方式，断言不变，应用不需要原repo/.git；测试后恢复该文件。2223个导出跟踪文件最终逐字节匹配358859a。

浏览器26=已有23+G1验收3，另替换3/空3；已有用例的加载/失败/并发含明确受控响应，新增9个验收用例来自真实API及页面筛选。截图在clean-delivery/screenshots。当前人工视觉抽查由agent查看original-1280，S03六月8—12日筛选、998元、27单、48销量、趋势/排行及质量台账展示完整；未将它写成用户本人审阅。

## 实际验收脚本错误（与产品失败分开）

1. 首次verify_rag把179项的混合HTTP目录直接给G2-04 audit，coverage.json没有records，产生KeyError。179项本身已通过。后按pytest实际收集的G2-04节点名选出82份HTTP再审计，90问答/90trace/61doc、来源身份错位0。原answer-audit.txt与顶层失败保留；answer-audit-corrected.txt为后续结果。修正后runner完整重跑尚未执行，不能写本次runner整体成功。
2. 最小A/B脚本初版把retrieve.text要求为“恰好一句事实”，导致带标题完整原文也被误判；heading-script-attempt保留。修正为事实在返回片段内且返回片段在该快照连续原文内，heading-repro表明四条retrieve都通过，只有两条无标题chat失败。未弱化chat期望。
3. compare.py固定标题写“与G2-03”，本次实际比较参数是G2-04 R1报告，见continuation-commands.json；vs-r1 JSON/表格实际为与R1逐题逐轮比较，49保持、无已过轮次回归。

## 移交与资源

- **已验证第二关阻塞**：无标题MD/HTML/GBK TXT正文被标题身份吞掉，回原G2-04修复，不能放入第三关待办。
- **已验证公开剩余失败**：V03/H01/H06/T01/T02/T03；具体检查在integration/eval/report.json与vs-r1.json。混合、多轮尚未实现；不把公开安全全过当完整对抗验收。
- **仅代码风险**：既有会话全局列表/未传history、混合旧_doc_block取证路径不同、启发式词项约束不等于一般语义蕴含；本次未做跨会话或任意混合事实证明。
- **尚未验证**：修复后的干净重跑、隐藏题、live、Linux、部署、完整安全对抗、聊天前端。

[resources.json](resources.json)：196个不同自建服务/进程组PID核对均已不存在；包含所有RAG、G1、独立夹具与A/B服务，短期服务finally退出。G1端口8015/8016/8017、全量63327已退出；无保留监听。未清理临时源码/环境。主checkout是唯一使用工作树，未动其他三个管理checkout。
[preservation.json](preservation.json)：2153受保护文件无改动。原未跟踪草稿/research仍在。此次只提交本目录材料；等待主会话恢复G2-04修复/合并后明确通知，再同步新main和重新验收。旧结果永久标注358859a，不冒充修复后结果。
