# G2-05 新环境最终交付证据

**本项实施与自验完成，等待主会话独立核验、合并和Issue状态确认。** 规格：[Issue #17](https://github.com/FHMinyi/moneki-ai-takehome/issues/17)。不由执行会话宣告Issue已验收关闭。

原评审固定点358859a；阻塞checkpoint d2a25c2完整保留在上级目录。PR22正文身份修复合并main4634dff后，正常merge到本分支，无冲突、无rebase。**新被测源码提交为 `b5c756e04302b14583b50ca83d07eee106285efa`**，业务字节与4634dff一致。新证据提交da4e4a8，随后仅整理报告；不得把358859a的结果充作新版本验证。

本轮：**公开无模型88.5/100、49/55全绿；199项真实RAG（16+19+62+82+20）、53原后端；浏览器26+3+3；原KB生命周期5阶段7问与标题A/B4问通过。** 未改生产业务、公开题库/评分器或两个checkpoint原脚本。根EVAL_REPORT并列17/25.5/41/88.5分，明确当前不是修复后真实模型成绩。

## 九项验收对应证据

| # | 结果 | 命令及证据 |
|---|---|---|
| 1 干净源码/新装依赖/三步 | PASS | G1 verify_delivery固定b5c756e导出，`make setup/rebuild/run`；clean-delivery/preflight.json、setup.txt、commands.json、environment.json、python-dependencies.txt |
| 2 原55题完整评测 | PASS | integration/commands.json中的eval/run_eval.py完整调用，未筛类别；eval/report.json、report.md；metrics6/6、data12/12（6题）、retrieval15/15、doc16/16（8题）、V01/V02、health全部通过 |
| 3 独立完整历史问句 | PASS | `test_history_boundary`5问，原文退款6/14旧7天→6/15新24小时，会员6/30赠50→7/1赠60，含全角日期；integration/rag-http逐问响应。V03原题第二轮仍失败，不能计整题通过 |
| 4 KB增改删/目录/格式编码/事实别名 | PASS | 原verify_kb.py：kb-lifecycle/result.json为5阶段7问通过；每阶段公开rebuild+重启+真实retrieve/chat，input-snapshots含独立原始字节、http.json含手写期望/请求/trace。原reproduce_heading.py四问也全过 |
| 5 十类诊断及新增真实RAG | PASS行为保证 | integration/collected-tests.txt实收集199、rag-regressions.txt全过；原53后端在clean-delivery/backend-tests.txt。旧诊断16过3失败（仅overlap拼接断言），原输出保留；偏移覆盖审计35篇215块遗漏0，75条HTTP身份错位0 |
| 6 第一关保持/输入保护 | PASS | 浏览器原始26、替换3、空3；真实页面筛选/展示和API独立手算一致，截图见下。2800个原保护文件未变，2865导出文件逐字节匹配被测commit |
| 7 最终阶段报告 | PASS | 根EVAL_REPORT第8节含原mock17/live25.5/G2起点41/本轮88.5，命令、commit、无Key配置及剩余六题；原始JSON/Markdown不改写 |
| 8 调试/AI/启动文档 | PASS | DEBUG_LOG保留逐缺陷红绿、失败猜测/实验/定位/commit，补本项回交过程；AI_USAGE明确工具、实际错误及决策归属；根README更新已验证摄取/重建/单轮API，三步入口不改 |
| 9 分层移交 | PASS | 下节分列已验证剩余失败、仅代码风险和未验能力；正文身份阻塞已回G2-04修复，原脚本在新安装环境重跑通过，不隐藏到第三关 |

## 实际复现流程和安装边界

工作目录 `/tmp/moneki-g1-05-6yeq26mj/source` 是git archive输出，没有.git；安装前无starter/.venv、frontend/node_modules/dist、starter/var/.cache、根和starter的.env.live。真实创建新venv、pip install和npm ci；可复用下载缓存，未复制任何已安装环境。macOS26.7 arm64、Python3.12.14、Node24.19.0、npm12.0.2、Make3.81，未在Linux实测。

本次从主checkout实际执行（新复现时更换输出目录）：

```bash
python3.12 docs/verification/g1-05/verify_delivery.py --commit b5c756e04302b14583b50ca83d07eee106285efa
python3.12 docs/verification/g2-05/verify_final.py --work /tmp/moneki-g1-05-6yeq26mj --out /tmp/moneki-g205-final-rag
PYTHONDONTWRITEBYTECODE=1 /tmp/moneki-g1-05-6yeq26mj/source/starter/.venv/bin/python docs/verification/g2-05/verify_kb.py --source /tmp/moneki-g1-05-6yeq26mj/source --out /tmp/moneki-g205-final-kb
PYTHONDONTWRITEBYTECODE=1 /tmp/moneki-g1-05-6yeq26mj/source/starter/.venv/bin/python docs/verification/g2-05/reproduce_heading.py --source /tmp/moneki-g1-05-6yeq26mj/source --out /tmp/moneki-g205-final-heading
```

第一条打印新建临时目录；后续--work/--source指向该次新目录，--out必须不存在。G1脚本依次完成三步、53后端/类型检查/metrics/原始浏览器、数据替换和空输入。第二条在同一新安装环境恢复原数据rebuild，启动make run，跑55题、199项和各审计。后两条仅从同一新导出复制应用模块到自己临时夹具目录，公开`python -m kbqa.rebuild`后启动真实HTTP。它们与第二条数据/缓存隔离，不使用原主checkout环境。

LLM_API_KEY/LLM_BASE_URL/LLM_MODEL及外部DATA_DIR/KB_DIR/VAR_DIR/TODAY明确移除；RAG runner还移除PYTHONPATH/VIRTUAL_ENV。服务health为mock、today=2026-09-01。无.env.live读取、无模型调用、无假模型服务。本次只有异常诊断两项向隔离副本注入错误；原53兼容测试自带固定检索fixture，不能用它证明真实RAG。

精确子命令/参数/cwd/退出码见[clean-delivery/commands.json](clean-delivery/commands.json)与[integration/commands.json](integration/commands.json)；[runner-logs](runner-logs/)是实际顶层stdout/stderr。G1 Make端口8015/8016/8017，集成端口60112。浏览器使用新安装Playwright依赖与缓存下载的Chromium，不复用旧node_modules。

## 应用字节与后加验证代码

[tested-tree.json](tested-tree.json)：2865个导出跟踪文件最终全部匹配b5c756e；业务与已审查main4634dff无差异。G1浏览器附加文件`frontend/tests/g1-05-delivery.spec.ts`的哈希在clean-delivery/tested-tree.json；未覆盖应用文件。

新runner在导出外运行；原两脚本的SHA与checkpoint逐字节核对：

- reproduce_heading.py：`6014f8ce3e5dfb817e1a67ac8cc63b8264aa857f8d3217dde1f8b0c766b19add`
- verify_kb.py：`8685a25a932ea1536cc037c88d103c4b06c65d73b20fa99acf2394634c8898ab`

两个缓存迁移测试需要历史代码：8b72f47的index.py/chunker.py，以及358859a的loader.py/units.py。runner从Git导出后设只读，仅把测试的git show获取式改为读取这些固定字节，其他断言保持；[verification-overlays.json](integration/verification-overlays.json)逐文件记录提交、哈希和覆盖哈希。测试结束恢复两份测试源码。实际应用不读取原repo/.git，不依赖旧venv。历史夹具存档在integration/history-fixture与heading-history-fixture，属于必要复现源码，不包含缓存或安装环境。

修正后的审计器输入按实际收集的82个G2-04测试节点名选取，不把coverage.json当HTTP；保留原审计断言，最终90问答/90trace/61doc来源身份错位0。vs-r1.md标题明确实际输入为G2-04 R1，JSON保留真实逐题逐轮结果，无回归。原错误日志仍在上级checkpoint，未改写。

## 输入替换、引用和历史完整性

| 阶段 | 实际输入/期望 | 已执行HTTP行为 |
|---|---|---|
| initial | 无标题MD：翡翠饭31分钟；Ivory Bowl别名表 | retrieve正分同源；chat31分钟连续引用 |
| add-html | 新HTML夜班配送19小时，含需排除的style/script | retrieve/chat19小时，仅可见原文；旧MD保留 |
| modify-format-encoding-alias | 原事实改47分钟，MD换GBK TXT；别名改Copper Dish | 新别名retrieve/chat47分钟；旧Ivory Bowl拒答；31分钟无残留 |
| delete | 删除HTML19小时文档 | 检索无旧19小时，问题refusal且无引用 |
| switch-directory | 指向另一目录、GBK TXT29小时及非文档README | retrieve/chat29小时正确；Copper Dish拒答；19/31/47旧事实无残留 |

每阶段期望来自脚本手写材料，不调用被测loader/index生成答案；每条返回片段及context_spans均与独立期望正文连续匹配，引用规范化后≤400字符、同源同块/表头，chat无经营数据证据；输入文件前后SHA相同。健康计数作为补充，未以缓存键/计数代替实际问答。

另外4问A/B覆盖无标题和显式标题×中文全称/英文别名，31分钟事实及连续引用均通过。20项heading回归覆盖标题本身不能当事实、相同标题/正文的不同位置、HTML内联标题、长Markdown跨窗口、纯TXT井号、旧缓存自动迁移。长标题英文已有保守refusal边界仍如实保留，不新增回答率门槛或改planner/阈值。

## 十类旧诊断与新发现问题对应

| 原缺陷 | 新环境执行的行为验证 |
|---|---|
| D01 格式遗漏 | test_original_identity_and_formats、test_format_through_rebuild_http，实际35篇 |
| D02 GBK | test_actual_gbk_exact_text、非法编码显式失败、新GBK事实替换 |
| D03 HTML | 可见正文/脚本样式排除、实体段落、HTML新增事实与引用 |
| D04 丢尾 | test_boundary_full_coverage十种长度、真实语料偏移覆盖、尾段/表格HTTP；g2-02-audit遗漏0 |
| D05 中文评分 | 15公开检索正分相关、自然变体/别名、正文支持审计 |
| D06 来源错位 | 去重/重排/补位身份，真实75条HTTP同源且错位0 |
| D07 版本过滤 | 现行/历史边界、5条完整历史问句及公开V01/V02 |
| D08 top-k后过滤 | 显式门店、先过滤再截断、top-k补位与问答证据隔离 |
| D09 缓存旧内容 | 增改删换目录、别名更新、两类真实旧缓存自动升级；本项7问逐阶段验证 |
| D10 健康虚报 | 空/非文档计数及原语料health35篇215块 |

旧诊断3个拼接断言因overlap重复而失败（301/600/601），16项通过，原始输出在diagnostic-original.txt。相同长度的严格原文偏移覆盖、0遗漏及真实尾段检索另证行为保证，不将原探针改绿或使用xfail。

实施中新问题已进入本轮199项：空白块/局部标题/长行表格、S03最小安全门禁、H05既有路径回归、主体属性同分句、普通/省略/否定问法、开放“什么”、NFKC引用长度、异常trace、无标题正文与结构标题位置。真实先红后绿和修复提交在前序README/DEBUG_LOG，checkpoint两次审查的中间输出都保留。

## 第一关浏览器与数据保护

原始26=已有23+G1-05实际验收3，另替换3/空输入3，三种宽度1280/1440/390；数据替换/空态API手算重跑，见clean-delivery/audit-replacement.json、audit-empty.json。已有加载/错误/并发测试使用明确受控响应；新增9个验收用例真实请求服务并操作筛选，不以控制响应冒充数据计算。

Agent本轮实际查看原始1280、替换390、空1440截图：原始S03六月8—12日显示998元/27单/48销量；替换X11显示22元净额/3.01退款及负值趋势；空输入显示无有效日期、零台账。390商品表滚至右侧是用例检查金额/销量，初始截图保留名称侧；没有把截图抽查写成用户本人审阅。

| 场景 | 1280 | 1440 | 390 |
|---|---|---|---|
| 原始筛选 | [截图](clean-delivery/screenshots/original-1280.png) | [截图](clean-delivery/screenshots/original-1440.png) | [截图](clean-delivery/screenshots/original-390.png) |
| 替换筛选 | [截图](clean-delivery/screenshots/replacement-1280.png) | [截图](clean-delivery/screenshots/replacement-1440.png) | [截图](clean-delivery/screenshots/replacement-390.png) |
| 空输入 | [截图](clean-delivery/screenshots/empty-1280.png) | [截图](clean-delivery/screenshots/empty-1440.png) | [截图](clean-delivery/screenshots/empty-390.png) |

[preservation.json](preservation.json)：2800个原数据/KB/题库评分器/前序诊断与证据/旧checkpoint/未提交材料哈希无变化。原草稿和research未吸收或删除。新证据及根报告属于本项允许新增/更新内容；根业务代码不变。

## 明确移交与边界

**已验证剩余失败**：V03/H01/H06/T01/T02/T03，详细失败check见eval/report.json；V03是第二轮追问失败，T01后两轮/T02第三轮/T03第二轮失败。H01与H06混合要求未满足。原已通过题与轮次无回归。当前评分不证明完整会话能力，公开安全9/9不证明完整对抗。

**仅代码风险/实现局限**：SessionStore全局历史且planner未接入历史的既有结构，本次未补跨session专门实验；混合旧_doc_block与纯文档取证路径不同，不能直接继承本关证明；中文二元词项/局部属性规则和保守门禁不等于语义蕴含；长标题低分时即使候选正文正确也可能refusal。用户已明确无Key允许保守拒答，本项不扩规则引擎。

**尚未验证或未执行**：隐藏题、修复后真实模型/LLM_SETUP最终接入复验、Linux、部署、长期稳定性、完整安全对抗、聊天UI、会话隔离和第三关混合编排。原真实模型25.5仅是原始基线。没有付费调用、部署或启动第三关。

无标题正文旧阻塞已回原任务修复，原断言在新基点通过；当前没有通过测试已发现且未报告的第二关共享证据阻塞。这个结论是本轮有限范围自验，仍须主会话独立核验。

## 资源与交付diff

[resources.json](resources.json)记录214个不同自建服务/进程组PID，全部finally退出并核对PID已不存在；G1端口8015/8016/8017、集成PID18816/端口60112已停。动态HTTP端口及停止状态逐条保留。无常驻自建服务，没有操作其他进程。

当前共享checkout `/Volumes/MACPSSD/project/moneki-ai-takehome`，分支codex/g2-05-acceptance，未新建worktree、未动其他三个管理checkout。保留：

- `/tmp/moneki-g1-05-6yeq26mj`：新源码、安装环境、G1数据夹具和构建/浏览器产物。
- `/tmp/moneki-g205-final-rag`：199项隔离源码/缓存、只读历史夹具、全量与诊断输出。
- `/tmp/moneki-g205-final-kb`、`/tmp/moneki-g205-final-heading`：独立KB输入/运行源码和完整HTTP。
- 上级resources.json中的358859a历史临时目录原样保留；未复用旧venv作为新环境。

相对审查后的main4634dff，交付仅G2-05复现脚本/证据和根README/EVAL_REPORT/DEBUG_LOG/AI_USAGE；没有业务代码差异。脚本和证据提交da4e4a8，最终文档提交在Git历史及PR中可查。等待主会话具体清理指令，不自行合并/关闭Issue或删除分支/环境。
