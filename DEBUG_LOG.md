# G1-01 调试记录

执行规格：GitHub Issue #1。实施固定点：`325954df96c73d18c8ddb68bf7539ac732d23632`。
分支：`codex/g1-01-data-quality`。清洗修复 commit：`0161f97`；工作区实现 commit：`748f8ab`。

实现与验收完成后收到提交/推送授权，按清洗、工作区、文档三个阶段整理提交。
下列修复前失败日志来自实际开发过程；没有为构造红绿历史回退代码或伪造提交。
本记录不替代此前两组全量评测，也不声明汇总、检索或模型接入问题已经修复。

## 1. 清洗未按 KB-001 执行

| 项 | 记录 |
|---|---|
| 现象 | 原始实现保留全部 18,628 行；手工 9 行夹具也全部保留，期望只留 3 行。 |
| 假设 | `clean_rows` 没有执行规范化、维表校验和去重，空金额被填 0。 |
| 验证 | 新增行为测试先运行，`before.txt` 中 `test_normalization_refunds_multiline_and_priority` 和 `test_sample_rebuild_is_repeatable_and_source_unchanged` 均失败。独立 CSV 脚本不导入生产解析器，核对六类数量。 |
| 根因 | 固定点 `starter/kbqa/cleaning.py:77` 的 `clean_rows` 原样追加每行；日期不解析，编号不规范化，金额失败时设为 0，所有 `removed` 计数保持 0。 |
| 修复 | `0161f97`。先执行 KB-001 四类规范化，再依次判断六项原因，仅记录首次命中；七字段去重，保留退款与合法多商品订单；源金额入分，不用商品单价回填。`removed_rows` 取六项之和。 |
| 回归测试 | 修复前 `before.txt`：保留 9≠3、18,628≠18,290。修复后 `after.txt`；六类 8/150/30/10/40/100，总剔除 338；日期 2026-05-01～2026-08-31；健康接口、质量接口和页面一致。 |

测试编写时先假定当前样本从 6 月开始，首次修复后该断言失败。
通过原始 CSV 和独立日期解析确认有 5 月数据后，将样本期望纠正为 5 月 1 日。
未据此改动生产解析规则。独立证据为 `independent-audit.json`，可用同目录 `audit_sample.py` 重跑。

## 2. 名为只读的数据库连接实际可写

| 项 | 记录 |
|---|---|
| 现象 | 对合成源库调用 `open_readonly` 后，`DELETE FROM sales` 未抛错。 |
| 假设 | 连接未启用 SQLite 的只读打开模式。 |
| 验证 | 修复前 `test_empty_and_readonly` 明确失败：`DID NOT RAISE OperationalError`。 |
| 根因 | 固定点 `starter/kbqa/cleaning.py:71` 使用普通 `sqlite3.connect(path)`。 |
| 修复 | `0161f97`。使用 URI `mode=ro`；源库及 DataTools 读取共享这个只读入口。 |
| 回归测试 | 同一测试修复后通过；样本连续两次重建前后 SHA-256 相同，结果行和台账相同。 |

## 3. 重建路径重合会覆盖原始数据

| 项 | 记录 |
|---|---|
| 现象 | 合成源库同时用作目标库时，原实现直接 unlink 并用清洗表替换源表。实验只对临时夹具执行。 |
| 假设 | 构建前缺少源/目标同一文件检查。 |
| 验证 | 修复前 `test_source_cannot_be_target` 失败：没有拒绝危险配置。 |
| 根因 | 固定点 `starter/kbqa/cleaning.py:140-142` 在无路径保护的情况下删除 target。 |
| 修复 | `0161f97`。拒绝相同解析路径和相同 inode；输出到同目录临时文件，成功后原子替换。 |
| 回归测试 | 同路径被拒绝且源字节不变；未定义的非数字金额使重建失败，已有清洗产物字节不变。 |

## 4. 浏览器验收脚本校准

首轮真实 API 的 1280、1440 通过；390 的末行位于纵向视口外，检查前补充滚动；
失败态“重试”由 Ant Design 渲染成带空格的可访问名称，定位改用 `/重\s*试/`。
这是测试定位问题，未据此修改页面业务。首轮结果保留于 `browser-first-run.txt`，最终结果见 `browser.txt`。
构建过程中 TypeScript 发现 Alert 使用了不属于 Ant Design 5 的 `title` 属性，已改为 `message`。

## 证据索引

所有路径相对仓库根目录：`docs/verification/g1-01/`。

- `before.txt`：实际修复前 4 项失败。
- `after.txt`：修复后后端回归。
- `audit_sample.py`、`independent-audit.json`：独立 CSV 核对。
- `build.txt`：类型检查及生产构建；Ant Design 的 use-client 指令和大 chunk 警告未阻断构建。
- `browser.txt`、`dev-proxy.txt`：生产同源 / 开发代理的真实 Chromium 验收。
- `workspace-1280.png`、`workspace-1440.png`、`workspace-390.png`：真实 API 页面。
- `loading.png`、`failure.png`、`empty.png`：受控响应下的反馈状态。
- `data-quality.json`、`health.json`：实际本地服务响应（mock 模式）。
- `preservation.json`：受保护的已跟踪数据、知识库、基线与固定点比较。

## 5. 规范化边界复核

| 项 | 记录 |
|---|---|
| 现象 | 仅含换行/回车的空金额未识别为空；原数量解析把小数截断成整数。 |
| 假设 | `parse_amount` 仅删除一组有限空白字符；`parse_qty` 使用 `int(Decimal(...))`。 |
| 验证 | `normalization-before.txt` 中手工夹具在修复前抛出非空金额错误；测试期望金额和数量分别被第 2、3 项剔除。 |
| 根因 | 固定点 cleaning.py 的 `parse_amount` / `parse_qty` 没有严格实现首尾空白与整数解析。 |
| 修复 | `0161f97`。金额先 `strip()`，去掉 `¥` 前缀，再 `strip()`；数量直接解析整数，解析失败按 0 走第 3 项。 |
| 回归测试 | `test_whitespace_amount_and_noninteger_quantity` 修复后通过，完整原始样本计数保持不变。 |

提交前再次核验：30 项后端测试通过、生产构建通过、5 项 Chromium 测试通过。
代码被测固定点为 `748f8ab`；随后仅补充文档和保存既有验收证据。
验收日志入库时仅清理 pytest 输出的行尾空白，未修改断言或测试结果。

# G1-02 调试记录

执行规格：Issue #2；固定点 `5b21ee3588c1cf3f6e8bea32f2dab4b6d22768d9`；
分支 `codex/g1-02-metrics-summary`。下列证据位于 `docs/verification/g1-02/`。
测试先实际执行，再修复生产代码；提交是在验证完成后按后端、前端、文档整理，
不将提交时间冒充测试执行时间，不回退代码补造红绿历史。

## 1. 汇总结束日丢失、退款遗漏、多商品订单被重复计数

- 现象：修复前 M01–M04 失败，M05 空区间通过；单日查询为零，手算两笔订单的净额和客单价不符。
- 根因：`DataTools._where` 用 `< end`；`query_metrics` 排除退款，退款固定 0、`COUNT(*)` 数明细、销量只累加销售。
- 验证：`before.txt` 是真实修复前 14 failed / 4 passed。手工夹具两笔订单三条销售：10+5.01+5=20.01，客单价 20.01/2=10.005 → 10.01；第二天原订单退款 3 元、1 份，单独当天 -3/3/0/null/-1。零金额行不属于销售。
- 修复：闭区间 `<= end`；金额包含退款，退款单独取绝对值；仅正金额销售行按 `order_id` 去重，销量按正负金额加减；金额保持整数分，客单价继续 Decimal ROUND_HALF_UP。每日指标共享同一闭区间，并排除零金额订单。
- 回归：`after.txt` 49 passed；包括 daily 的补零/单日/退款/零金额，以及现有 payment_mix、top_products、by_store、by_store_category、compare_periods 的结束日边界。未增加趋势/排行 UI，也未重做这些工具的其他行为。
- 独立证据：`audit_api.py` 复用 G1-01 的独立原始 CSV 规范化脚本（无生产导入），再独立 Decimal 聚合；8 组 API 对照全部一致，见 `independent-api.json`。固定样本预期只在测试数据。
- 公开评测器：`public-metrics.txt` 与 `public-metrics/report.json` 证明 M01–M06 6/6；这不是全量评测，也没有真实模型调用。

## 2. 日期错误被接受为经营查询、页面缺乏筛选入口

- 根因：`date.fromisoformat` 接受紧凑日期/ISO 周日期；没有检查 start > end；原前端仅数据质量台账。
- 修复：summary/daily 要求严格 YYYY-MM-DD、有效日历日期、顺序合法，错误返回 400 与中文 error；新增只读 `/api/stores` 从实际维表取选项。
- 前端：Dashboard 统一持有已生效条件；DashboardFilter 保存草稿、明确查询才生效；校验失败不发请求，提示旧条件仍生效。初始日期来自清洗后真实范围。SummaryPanel 渲染五项指标、加载/失败/重试/空结果，null 客单价显示“—”与无可计算值解释，退款区间不被误判为空。
- 并发：公共请求 hook 用 AbortController、15 秒超时与 active 标记；返回值携带 URL/revision，防止条件切换后的首帧显示旧结果。浏览器特意让 fetch 忽略取消信号、延迟旧成功响应，确认新空区间保持 0/null。
- 证据：`browser.txt` 11 passed（6 项本任务 + 5 项 G1-01 回归），1280/1440/390 实际 Chromium、实际 API；`dev-proxy.txt` 1 passed。退款专属显示/失败/延迟为明确受控响应，其余真实页面与 API 核对。

## 3. 实际开发中的测试/构建调整

- `fixture-first-run.txt`：最初合成源库把数量存成 int，生产清洗器按 POS 的文本字段调用 strip，4 个夹具初始化错误。改为源数据结构一致的字符串数量后才形成 `before.txt`；没有改生产解析器迎合夹具。
- `build-first-run.txt`：Vite 配置加入可覆盖代理目标后 TypeScript 缺 Node 类型；补开发依赖 `@types/node`，最终构建通过。已有 Ant Design 指令与 bundle 大小警告仍非阻断。
- `browser-first-run.txt`：AntD 的透明搜索 input 被选中项挡住，click 定位超时；测试改为键盘 ArrowDown 打开，再点击真实选项。首轮仍运行时测试源码已修订，因此其错误代码片段展示的是当时磁盘上的新文本，调用日志保留真实 click 超时；不把这个失败归因于业务数据。
- `select-before.txt` 实际是一次通过的诊断运行，检查 aria-expanded=false，未据此修生产代码。随后确认截图捕获了收起动画，补等待 dropdown 隐藏，再保存清晰截图。
- 所有 G1-01 回归截图写入本任务子目录 `g1-01-regression/`；原证据、原数据、知识库、两组基线与固定点逐文件一致，见 `preservation.json`。原有未跟踪草稿及 research 仍保留。

实现提交：后端 `8fa078c`；前端 `54f327c`。其后仅补充文档与已生成验收证据。
保护核验首次遇到 Git 对中文路径的 quoted 输出，改用 `ls-tree -rz` 读取 NUL 分隔真实路径后，103 个受保护已跟踪文件逐字节一致。


# G1-05 调试记录

规格 Issue #5；执行起点 `839ec491cc80dbd79f677bf045446e2e4adfc254`。本轮不重新编造前序红绿历史。

## 1. 源码导出携带预生成索引

| 项 | 记录 |
| --- | --- |
| 现象 | 对入口提交 `e842093` 做 git archive 后，安装前“没有 starter/.cache”断言实际失败；依赖尚未安装。 |
| 假设 | 初始把已有 `.gitignore` 当作导出时不会带缓存的保证。 |
| 验证 | `git ls-files 'starter/.cache/*'` 返回 `starter/.cache/index.json`，证实文件已被跟踪。失败记录见 `docs/verification/g1-05/clean-export-before.txt`。 |
| 根因 | 固定点中的 `starter/.cache/index.json:1` 为已跟踪生成物；`.gitignore` 只忽略未跟踪文件，不能把已跟踪缓存从 git archive 排除。`starter/kbqa/config.py` 的旧注释也说明缓存随仓库分发。 |
| 修复 | `6d42e85`：`git rm --cached starter/.cache/index.json`，保留本地文件且沿用现有 ignore；更新注释。不改缓存键、loader 或检索算法。 |
| 回归测试 | 正式导出前置路径缺失断言通过，`preflight.json` 保存被测提交与七个缺失路径；随后的三步安装/重建生成新索引与完整页面，`generated-artifacts.json` 保存产物 SHA-256。可用 `verify_delivery.py --commit 6d42e85` 复现。 |

## 2. 验收和版本边界

没有发现需要修改看板口径或精修页面的第一关阻塞缺陷，因此未为制造改动而增加业务修复。
53 项后端、26+3+3 项浏览器、M01–M06 6/6，以及真实替换/空销售重建均通过。
所有被测应用文件为 `6d42e85`；后续只增加验收脚本、日志、截图及文档。新浏览器脚本是验证附加文件，散列记录在 `tested-tree.json`。

实际准备过程中，第一次缺失断言失败后尚无工作目录指针，紧接的 shell 安装命令因此未进入目录、以错误退出，没有安装运行环境。
修复缓存分发后重新导出到明确的 `/tmp` 目录，才运行成功的安装步骤；没有把第一次尝试写成成功。

本轮仍观测到健康 `kb_docs=36`、缓存键不感知知识库内容等前序问题，它们属于后续 RAG 范围。
N01 的清洗字段已核对，未将 N01 整题说成通过；构建 chunk 提示及测试依赖弃用提示见真实日志。

## G2-01：可信摄取、重建和健康计数（2026-09-27）

执行基点 `acfcabd5bf0fa69b8d54e4d948ee07a2f8a4a8ce`，Issue #13；红灯提交 `ac14efd`，修复提交 `1e4ebbe`。
完整命令、真实 HTTP 与原文对照见 [G2-01 验证](docs/verification/g2-01/README.md)。以下修复前行号均指执行基点，修复后行号指 `1e4ebbe`。

| 缺陷 | 现象与假设 | 实际验证与关键输出 | 根因与修复 | 回归及修复前证据 |
|---|---|---|---|---|
| D01 格式遗漏 | 实际 KB 缺三篇；假设白名单仅接受 Markdown | 实际文件身份集合与索引比较失败；TXT/HTML 经 rebuild + HTTP 也失败。排除只在 loader 单测里出现的问题 | 旧 `loader.py:12,233` 排除 txt/html；新 `loader.py:13` 扩充实际格式，修复 `1e4ebbe` | `test_original_identity_and_formats`、`test_format_through_rebuild_http`；`red.txt` 与 `red-http/` → `green.txt`，原始库35篇/88片段 |
| 文件身份违约 | front matter 可把 KB-901 变成 KB-999；推测编号优先级反了 | 不一致编号断言实际返回 KB-999；无编号 README 的排除也纳入同一回归 | 旧 `loader.py:185-186` 优先读 meta；新 `loader.py:221-243` 先验证文件名，冲突告警，修复 `1e4ebbe` | `test_filename_identity_not_frontmatter`，`red.txt` → `green.txt` |
| D02 编码吞字 | GBK 通知中文损坏；假设 errors=ignore 静默丢字 | 与真实源文件严格 GBK 解码逐字比对失败；无效字节原实现未抛异常 | 旧 `loader.py:82-84`；新 `loader.py:126-136` 严格 UTF-8/BOM → GBK 回退并告警；两者均非法时显式失败，修复 `1e4ebbe` | `test_actual_gbk_exact_text`、`test_invalid_encoding_never_silently_drops_bytes`；原文/加载全文及 SHA-256 在 `source-comparisons.json` |
| D03 HTML 非正文 | HTML 仍含脚本；假设仅抽取 title 没转换正文 | 真实 FAQ 命中 window.dataLayer；小夹具验证段落、br、实体、head/script/style 隔离，均先失败 | 旧 `loader.py:178-182`；新 `loader.py:80-123,233-239` 使用标准库 HTMLParser 抽取静态文本；修复 `1e4ebbe` | `test_actual_html_visible_text`、`test_html_paragraphs_and_entities`；`source-comparisons.json` 保存原 HTML、加载文本及连续引文 |
| D09 缓存不感知输入 | 增删改和换目录后仍旧事实；假设缓存只绑定版本 | 四个独立 HTTP 生命周期回归全部先红；别名/标题更新也先红。临时副本排除共享旧缓存干扰 | 旧 `index.py:23-27` 仅版本键、`rebuild.py:22` 可复用旧缓存；新 `index.py:23-36` 绑定路径/文件名/字节/解析版本，`rebuild.py:22` 强制刷新，修复 `1e4ebbe` | `test_lifecycle_rebuild_restart_http`、`test_metadata_alias_refresh_and_automatic_cache_invalidation`、`test_first_start_and_legacy_cache_upgrade`；15项红灯含旧索引升级。另补公开重建/重启后别名、门店元数据和删除清除验证 |
| D10 健康虚报 | 空文档库放 README 后 health=1/index=0；假设计数用目录文件数 | 真实 HTTP 空库回归先失败；完整库修复后 health=35/index=35/chunks=88 | 旧/新 `service.py:70`，改为 len(index.docs_meta)，修复 `1e4ebbe` | `test_empty_and_non_document_health`；`red-http/` → `green-http/`，`integration/health.json` |

执行中的测试脚本错误：首轮证据文件名使用参数化 HTML 字符串，含 `/` 导致写证据报错；修正为安全文件名后，在尚未改产品代码的基线上重新运行，最终提交的 `red.txt` 为15失败、无测试框架错误。旧缓存夹具由真实基线代码生成，未用检索替身。

原后端53项通过；新增16项最终全绿；公开 metrics 6/6、data 12/12，未退化。无模型全量43/100、27/55题全绿。
原诊断仍7失败/12通过（两次）：分块尾段3例、中文匹配、来源映射、现行版本过滤、top-k过滤。审计显示35篇均有尾段未进入片段、累计5940字符；全文仍在索引。未修改这些后续层，也未把公开检索8/15或零分补位解释为真实相关性完成。修复提交：后续项均待修复。

## G2-02：完整证据与来源一致性（2026-09-27）

固定点 `8b72f47`，Issue #14。[命令、HTTP与逐项证据](docs/verification/g2-02/README.md)。旧代码行号指固定点，新代码行号指最终业务提交 `b1d57c8`。

| 缺陷 | 现象与真实假设 | 实验及关键输出 | 根因和修复 | 回归/修复前红灯 |
|---|---|---|---|---|
| D04 丢尾段/空正文伪证据 | 长度301丢1字、600丢300字；尾段事实HTTP没有正分。猜测range扣减造成尾部遗漏 | 独立长度边界与真实库逐篇审计；35篇原有遗漏5940字；空正文回退元数据title不在原文中 | 旧chunker.py:41的range终点及:54回退标题。`2e4c2e4`完整覆盖/空正文不制造块；最终chunker.py:38-68 | `b0244ce`的chunk-red.txt 11失败3通过，边界/实际库/tail HTTP；最终audit.json未覆盖0字 |
| D04 表格/标题与连续引用 | 40行表格末行被截成rowt，猜测固定字符窗口既丢尾又拆行 | 独立真实HTTP rowtoken先无完整命中；修复后末行77正分返回，标题和表头均带同文档位置。连续行cite成功，合成检索文本cite被拒绝 | 旧chunker.py:42盲切；`2e4c2e4`新增整行分组、局部标题、source_start/end/context_spans；最终chunker.py:79-125，retriever.py:51-61明确HTTP原文/检索文本分离 | chunk-red-http → chunk-green-http；后补长行、父子标题和表格外不残留表头回归，19项最终全绿 |
| 布局缓存一致性 | 新布局不能继续使用旧片段；原实现注释已有版本契约 | 在同临时目录实际装入8b72f47的index/chunker生成旧缓存，然后恢复新代码自动启动；tailtoken重新可见。另只改大小180导致key/chunks变化 | `2e4c2e4` index.py:26加入layout_signature，语义版本最终chunker-4，参数直接参与键；未手工删除缓存 | test_offsets_context_and_cache_layout；相同输入payload、身份和检索顺序一致；原红灯无偏移字段 |
| D06 去重后来源错位 | 多高分片段夹具中KB-902#1被标KB-901；实际R08 KB-011#6被标KB-010 | 真实HTTP与内部Hit/meta/索引双向比对均先失败；排除单纯前端展示或夹具mock问题 | 旧retriever.py:264,275-276按未经去重ordered再覆盖doc_id。`d4995b3`删除覆盖，始终用同一position构造完整Hit | `b5a94c5` identity-red.txt 2失败；独立夹具含去重、重排及正/零分补位；R08/R10与全15问75条均一致 |
| 自引入碎片问题 | 首轮集成35篇360片段，额外审计发现20片段仅空白；猜测标题独立emit使边界空白成片 | test_headings_and_spacing_stay_with_body在c1a9acb先失败。修复后全文覆盖不变、35篇215片段且无空白块 | 初修2e4c2e4 chunker.py:103单独emit标题，文本分支另发空白。`b1d57c8`标题随下段、空白并前连续正文（最终:79-86、103-125） | spacing-red.txt → spacing-green.txt 19通过；首轮integration-before-spacing和最终integration分别保存 |

本轮测试编写出现一次字符串转义导致的SyntaxError，保留test-authoring-error.txt；修正测试后继续验证，没有当作产品失败或伪造历史。未调用付费模型。
最终19项本任务回归、16项G2-01、53项原后端通过；无模型44/100，28/55，metrics6/6和data12/12未退化。检索9/15、doc0/16、version0/6如实移交后续任务。

## G2-03：相关且适用的检索（2026-09-27）

固定点 `4a07686449337322c87520ebca52ac838ede86db`，Issue #15。完整命令、8项验收及原始HTTP见 [G2-03证据](docs/verification/g2-03/README.md)。未改公开题库、评分器、原始输入或前序证据。以下是实际发生的实验，不以金标编号命中替代正文支持。

| 缺陷 | 现象/当时假设 | 实验和排除 | 根因/修复 | 真实红绿 |
|---|---|---|---|---|
| D05 中文无法评分 | 自然中文整句被当成一个空格词；怀疑词项没有交集 | 固定语料比较空格、单字、二元、单字+二元，正分金标分别8/14/15/15；排除“必须引入向量服务”，选择二元降低单字噪声 | 基点tokenizer.py:20-22；`ea1d7e4`改为NFKC后中文二元/英文数字整词并升级tokenizer缓存版本 | `d12c517`封存基点30失败9通过；lexical-green.txt 26通过 |
| D07 版本和历史日期 | 当前退款仍返回旧版；完整历史问句不能正确限定 | 两版本夹具+实际退款2026-06-14/15边界；含“当时”的日期不得绕过有效期 | 基点loader.py:67写state，retriever.py:120读status，historical直接跳过日期；`a89f28e`统一status、升级loader缓存、按[生效日,取代日)筛选 | `99c3f29` scope-red.txt 12失败1通过→scope-green.txt 39通过 |
| D08 门店和top-k | S02有候选却先选S01再过滤；不足top-k；补位不透明 | 两文档top_k=1/2/5/100；真实KB020显式S03与KB001正文S01举例对照；chat及工具验证补位不作事实 | 基点retriever.py:240/307先排序后删；`a89f28e`先allowed集合再打分，最后零分补排除项；Hit输出padded/evidence_eligible/exclusion_reason，ranked及search_kb工具隔离 | scope-red/green；额外actual_store、tool_uses与unknown检查。源码entities.py门店ASCII边界同时支持中文紧贴/全角编号 |
| 正分但只有标题 | 15题都命中gold后，人工读实际text发现R04只返回SUPPLY RESUMPTION，R10只有议题标题 | 两条独立内容支持红灯；源正文事实形状权重1/1.5/2/3实际对照，1失败而1.5起两条通过 | BM25长度归一和重复标题上下文偏爱短标题；`eb1d1f9`复用已有通用focus_kinds/carries，仅给已有正分候选乘1.5，不造新候选 | `2c7ce73` support-red 2失败→support-green 41通过；换事实/别名及仅有金额形状无词项反例也通过 |
| 全角日期调用不一致 | 同完整历史问题的chat trace与retrieve选中不同版本 | 全角2026/06/14经retrieve正常归一，planner原parse_time未归一；真实HTTP对比hits和scope | timeparse.py:96原直接删空格；`8841a2e`共享解析入口NFKC归一（含loose_days） | `5f3efd7` extra.txt 1失败5通过→extra-green.txt 6通过 |
| 跨语言别名低权重 | 鲑鱼波奇饭赔付变体的邮件证据排第6（7.6713分），未入top5 | 别名权重0.6/1/1.5/2比较：15/16、16/16、16/16、16/16；选与文字词项同权1.0 | retriever.py别名已表示同一概念却固定0.6；`a4ccc7f`改1.0，无题号/文档/金额分支 | `f1e71f9` shape-extra.txt 1失败2通过→final.txt 50通过 |
| 检索增强暴露明确拒答回归 | 首轮全量50分但S03由无命中偶然拒答变为拼资料，safety3→0；S02也仍错误作答 | 主会话要求本项最小补救；7种完整攻击/全半角/后置探测+5种正常只读；源pos.db及隔离clean.db请求前后SHA256相同 | Planner.plan未接入已有is_destructive/is_prompt_probe；`8b4d757`在scout前调用，trace保留prohibited_request；不改全文拼接或正常投诉事实选择 | `75908de` guard-red 7失败5通过；接门禁后guard-initial 1失败11通过，剩余为SQL边界 |
| SQL动词紧贴中文漏判 | 全角DROP已NFKC转成英文，仍穿过刚接入的门禁 | 最小输入“请帮我执行ＤＲＯＰ　ＴＡＢＬＥ　ｓａｌｅｓ”真实HTTP返回doc；正常完整英文与中文删除被拦截，排除归一失败 | entities.py的_SQL_WRITE用Unicode词边界，中文也是word；改ASCII标识符边界，沿用既有动词/对象组合；修复`46bbd94` | guard-initial原始1失败保留；guard-final与最终全套见验收README |

测试编写/证据保存失误也保留：首轮误写门店别名和退款生效日，按KB003/013原文修正后才封存正式红灯；替换别名初版共享Bowl，合法词项命中被误当缓存残留，换不共享词项再测；长攻击问句作文件名超过macOS限制，改短测试ID重跑。详情 `test-authoring.md`，原失败文件未覆盖。第一个红灯提交时输出仍在写入，紧接着`d12c517`在任何产品修复前补齐最终30失败结果。

范围裁定：明确越权/写操作/系统探测的拒答回归是主会话基于真实全评要求的最小补救，[Issue进度评论](https://github.com/FHMinyi/moneki-ai-takehome/issues/15#issuecomment-5849393695)记录边界。未修G2-04完整单轮路由、错误句子选择/全文拼接，也未完成第三关安全对抗、多轮或真实模型验收。首轮及最终全量报告均保留，剩余失败按题号诚实移交。

## G2-04：单轮文档事实、连续引用和路由（2026-09-27）

固定点 `174cc635b7ae547b939bcbfb03091af7e3b59916`，Issue #16；执行模型 GPT-6 Astra/high。以下记录的是实际观察与实验，不把公开题通过当作充分证据。完整原始输出、命令及验收映射见 [G2-04](docs/verification/g2-04/README.md)。未修改原始KB、数据或公开题库评分器。

| 缺陷 | 现象、假设与实际实验 | 根因位置（固定点，另标明新引入者） | 修复及先红后绿 |
|---|---|---|---|
| 数量词覆盖文档路由 | 退款时限、周五营业时间、员工迟到、充值赠送被当成数据问题；真实plan trace说明检索尚未决定事实就已误路由。当前时间还触发销售范围拒答 | `planner.py:258-265`按“多少/多久/几”无条件覆盖；payment词表把充值语境视为支付构成 | `a4647d8` red 23失败4通过；`ff6860b`只由真实数据能力决定查数，11路由通过 |
| 升序选句、全文泄漏、无界扩引 | 路由修好后，退款引用停业通知，营业时间引用FAQ元数据；C04虽取到赔付句，全文拼接仍可带无关事实。假设排序及整篇扫描导致；真实HTTP排除loader、缓存和固定检索替身 | `answerer.py:77`升序；`:133`截断200字符；`:142`整篇rank；`:313-320`拼入命中文档所有块，`:355`加到答案 | `74583d2` evidence-red 15失败1通过；`b77de97`单轮改用 `_document_evidence`，只在ranked正分适用块原文范围内选句、降序排序；表格表头另附连续引用；27项绿灯。旧混合分支不整体重写 |
| 事件月份误作资料截止时点 | 7月投诉汇总在8月发布，被按7月底过滤，导致S01引用其他资料；trace里KB060为future，排除“缺文件”假设 | `planner.py:99`对所有问题统一spec.as_of；`retriever.py`按有效时点正确过滤，问题在调用语义 | `b77de97`在文档非政策/非历史语境用today作资料适用时点；完整政策日期仍保留。S01引用出餐慢12条，当前/历史边界分别测试 |
| 单位和缺失属性误答 | “几天办结”答“迟到3次”；花生含量答销量；进一步加入身份证、积分抵扣、花生布尔问题，原文主题相近仍答无关事实。以正例叠加/提现/审批检查拒答是否过度 | `docfacts.py:119-149`只看宽泛值形状与主题权重，未知词被term_weights丢弃；单有主题不是属性支持 | `b77de97`显式请求单位限制；`3b552a9`变体红灯→`6d58a28`识别通用“时限/期限”；`c647296`属性及正例4失败2通过→`d916238`48项通过。未知末尾属性保留，布尔问题不误要求金额形状 |
| 异常丢失 | 分别在隔离副本planner和取证调用处注入RuntimeError；HTTP200/refusal有了，但trace.errors为空 | `service.py:175-180`吞异常不记录 | `a4647d8`两项红灯；`b77de97`记录trace.error和logger.exception，HTTP仍合法。只在异常诊断测试注入，不替换RAG检索 |
| NFKC引用长度溢出 | 含兼容字符㈱的真实表格行，原字数短，规范化后428字；第一个探针被低相关拒答遮住，加入“规定”语境才穿透并失败 | 初修 `b77de97`的`DocFacts.cite`只去空白计算长度，没有NFKC及Markdown规范化 | `9287808`保存实际428>400红灯；`94b41e0`按契约规范化计算，过长引用不采用，HTTP合法拒答 |
| 本项引入H05既有回归 | 首次全量85.5分但逐题对照H05从3降0；原题和不同问法两项真实HTTP均返回doc无数据证据，未用上涨分数掩盖 | `ff6860b`移除数量覆盖时保留的why分支变为独立if，覆盖了本应保留的payment数据路线；非混合取证本身问题 | `be64b0f`2项红灯；`67b0f62`仅在非真实数据数量意图时why覆盖为doc，复用既有payment及cause路径；13项（含11条文档路由）绿灯。85.5分报告保留于first-integration和integration |

测试/记录错误如实保留于 `test-authoring.md`：最初把旧退款期限误写2小时，原文为7天；取证方法改名后一次异常注入未命中目标；74583d2提交说明把16项误写16失败，实际15失败1通过；NFKC首探针没有暴露溢出，不能当红灯。以上均没有倒改原始输出。

最终业务提交 `67b0f6255c2e1c2de1bd6e13c14a8a72c9ee5b3d`；本项51项、G2-01—03共97项、原后端53项；最终无模型88.5/100，49/55整题全绿。对前序36个全绿题及原已通过轮次逐项比较，全部保持；新增13个整题全绿，仍未全绿V03/H01/H06/T01/T02/T03。V03只新增第一轮通过，不把历史完整问句当成追问通过。最终真实执行结果与命令保存在G2-04目录；没有部署或真实模型验收。

## G2-04 主会话审查修正 R1：自然问法不能绕过事实支持（2026-09-27）

主会话在PR #21独立跑通51项后，额外真实HTTP发现三个合并阻塞：外卖退款“要提供身份证吗”、员工迟到“能用积分抵扣吗”、牛肉poke“里有花生吗”均误答其他事实；“是否含花生”却正确拒答。主会话原始四问response/trace保留于 `review-r1-parent-probe.json`。这说明上一轮第5/6项自验覆盖不足，不能将先前51项通过当作该问题已经解决。未改写旧88.5分报告。

| 现象/真实假设 | 实验和根因 | 红灯与修复 |
|---|---|---|
| 自然吗问句、正反问漏掉属性约束 | `f2d2fff`的docfacts.py:97只从部分固定布尔标记取tail，返回空列表后_answerer把问题当普通主题抽句。题目含主题并不支持所问事实 | `33a6427`：17项8失败9通过；另同句分号跨主体1失败。`3e53810`改为先解析闭合问题的主体/所问属性，再要求它们在同一分句内有支持；未知属性不因词表不存在被丢掉，已识别实体必须同源对应。69项通过 |
| 属性词存在于另一主体，甚至同句另一分句 | 合成材料同时写“员工迟到登记”和“会员消费可用积分抵扣”；旧代码把后者转移给前者。原文词项有交集仍不构成主体关系支持 | `test_boolean_subject_and_replacement`真实改材料，把权限归属从会员换为员工，重建重启后可回答/拒答随归属互换；`test_boolean_subject_cannot_cross_clauses`在同一原文单元内用分号隔开两个主体，禁止跨分句借用 |
| 省略吗/问号或否定能愿词仍需约束 | 在前一修复上继续测试“要提供身份证？”和无标点文本，以及不能/不可以正常对照；缺显式语气词仍落回主题抽取 | `8297bb1`：11项10失败1通过（3个正常对照的失败为trace缺少claim解析）。`705bdc4`以通用关系词与开放疑问区别闭合问句，保留否定能愿词的主体边界；80项通过 |
| 新引入“什么”末字误判 | 完整评测86.5分；逐轮对照发现V03首轮和T02第二轮回归，整题全绿数49不变也不能掩盖。真实最小问句的required_claim错误地把“什么”的么当末尾语气词，属性被截成“什” | `b8689a7`保存2项HTTP红灯及86.5分报告；`c713077`让开放疑问词优先，31项自然布尔与开放疑问对照通过。未修会话继承或新增混合编排 |

第一轮主体归一化删除了末尾“申请”，使退款审批正常对照从足够完整的主体降为过短词项组合，4项被误拒；`review-r1-attempt.txt`保存4失败20通过。恢复主体文本后原始/自然审批对照通过，不降低断言，也不以“一律拒答布尔问题”修复。

R1仍是无模型的保守抽取校验，不是形式化语义蕴含或通用中文解析器。产品没有身份证/花生/积分等领域属性列表，没有整句、题号、KB编号或答案值分支。返回的是有同主体同分句支持的原文，不凭主题匹配生成肯定/否定结论。最终回归/全量/资源与逐轮对照见G2-04 README的R1节。

R1最终被测c713077：82本项、97前序、53原后端通过；完整无模型88.5/100、49/55。对G2-03及原88.5交付逐题逐轮均无已通过回归；90次问答trace、61次doc取证身份核对无错位。原保护905文件无变化，R1新增519次自建服务全部退出，最终PID61358/54267。

## G2-04 heading follow-up：G2-05发现的正文身份缺陷

G2-05在新环境替换KB时发现：KB970表格别名翡翠饭/Ivory Bowl，KB971只有“翡翠饭的配送时限为31分钟。”；retrieve正分原文正确，中文/英文chat均refusal且evidence.candidates为空。仅加显式标题后四条A/B中的两条原失败转绿。来源为G2-05检查点d2a25c2；主会话重开Issue16并交回本会话小修。固定点358859a，不合并G2-05检查点提交。

| 问题 | 假设、实验与根因 | 红绿与修复 |
|---|---|---|
| 推断展示标题吞正文 | 原loader.py:204-209,252从首正文推断title，chunker.py:90把它加入heading，units.py:117-119,148-152按文本相等标heading，docfacts.rank再排除。真实retrieve有证据、中文同样失败，排除单纯别名问题 | 04b435d先保存15项11失败4通过及原G2-05脚本红灯。3dc0d3f只让源结构决定标题身份；MD沿用原结构，HTML附加可见正文heading_spans，loader-4自动使旧缓存失效 |
| 同名标题/正文及格式身份 | 同文字在显式标题与正文各出现一次时仍被去重吞掉；TXT的#不应当Markdown格式。真实四格式/同名/元数据对照先失败 | units.py去重区分heading/text，只有Markdown结构去掉ATX标记，HTML按实际h1—h6原文位置识别；31→47重建更新及旧代码缓存启动控制通过 |
| 真标题多句/跨窗口 | 初修只看每句的#前缀，多句标题的后一句或长标题第二块会落成text；真实HTTP观察候选中出现标题事实 | 4f95a04保存两条结构红灯；31d2c64复用已有Markdown context_spans的完整位置，真标题不当正文，连续来源不变 |

实现首轮错误也保留：默认heading_spans初始化误放parse_front_matter，load_document重建UnboundLocalError；green.txt实际15失败，first-attempt.patch可还原当时未提交候选。修正后green-2为14通过1项自增回答率假设失败。

自增长Markdown标题的英文问题已选中原文，却因6.6644分和既有underspecified门禁refusal。主会话按用户对无模型过度开发的质疑明确收敛：不把自增“长标题也一定答出”作为新门槛，不改planner/阈值/别名语言规则。旧失败及旧断言保留，测试仅按裁定改验正文身份/连续映射，允许当前保守拒答；原G2-05两脚本输入和断言未改。详见heading-fix/expectation-scope.md。

最终精确业务提交31d2c648c8fb6849514a2a59d3d034b579ee39f4：原G2-05两脚本SHA与检查点一致，逐产品文件比对提交字节后运行，A/B4问、生命周期5阶段7问全绿。20本项、179前序、53原后端通过；全量仍88.5/100、49/55，逐题逐轮无原已通过回归。35篇215块原文遗漏0、75来源错位0。源码仅loader.py/units.py变化，未改语言路由或评分参数。完整命令、文件和资源见docs/verification/g2-04-heading-fix/README.md。

## G2-05：独立整体验收与阻塞回交（2026-09-27）

本项验证/报告为主，未增加产品规则。首次固定358859a新装环境，公开88.5分、179项RAG和第一关浏览器通过，独立KB替换却暴露正文身份问题。最初假设别名未被取证层正确使用；中文全称同样失败、只加标题后两种问法都通过，排除“仅别名失败”。完整四问A/B、格式生命周期、原输入与红灯提交d2a25c2见G2-05 checkpoint。根因与修复commit见上节G2-04 heading follow-up；不得以公开同分或补标题夹具掩盖共享证据缺陷。

主会话退回G2-04，修复3dc0d3f/31d2c64经PR22审查合并4634dff后，本项正常merge为b5c756e，再git archive全新导出/venv/npm ci；没有复用旧安装环境冒充新版本验收。原两脚本SHA保持不变，5阶段7问与4问A/B全过；所有实际新结果集中在docs/verification/g2-05/final，旧失败未覆盖。

验收工具自身两次错误也保留：混合179项证据目录含coverage.json，G2-04审计器按HTTP records读取导致KeyError；改为根据G2-04实际收集的测试节点名筛选，保持审计断言不变。初版A/B要求retrieve.text恰好为一句事实，误判带标题连续片段；改为事实包含于片段、片段包含于该次完整原文，保留chat精确事实/引用要求。当前新环境整套运行已验证这些调整；compare输出标题改为实际比较的G2-04 R1，而不是旧脚本固定的G2-03。

旧诊断301/600/601直接拼接断言仍因overlap重复而失败，原输出保留。G2-02的原文偏移覆盖、十种长度、真实语料尾段和同源上下文另行证明不丢字，未采用xfail/跳过/删断言变绿。只读历史模块夹具仅替代测试中的git show获取方式，应用运行不依赖原repo/.git；旧模块和覆盖字节哈希都保存。

本关约定之外的无Key保守refusal是已知限制，不能把任意新中文问法或长标题回答率升级为继续扩张规则引擎的理由。若真实返回无关事实、丢正文、错引或换库失效，仍是共享证据缺陷。已验证失败、仅代码风险、尚未验证能力分别移交，见final/README.md。

## G3-01：单轮查数来源、工具边界与会话隔离

前置时间边界：2026-09-27 12:50:42，在业务字节仍为2839c67时仅运行本票新增探针，9失败/1通过；红灯提交3686878。修改前未重跑完整55题、53原后端、199 RAG或preflight；此前引用的是第二关历史证据。后续绿灯均为本票修改后结果，不是前置完整基线。

| 现象 | 假设与验证 | 根因 | 修复 | 回归证据 |
|---|---|---|---|---|
| B会话读到A历史；返回对象还能改动已存slots | 直接交错两个session并修改读取快照，排除模型理解问题 | sessions.py仅有一个共享列表，忽略session_id，浅复制 | 有界OrderedDict按session存储、深复制、无ID不存 | test_sessions_are_isolated_and_snapshots_are_detached，red.txt失败→green.txt通过；HTTP interleaved |
| run_sql在模型工具列表；额外参数被丢弃后仍查询 | 真实Service工具入口+查询spy；日期倒置、非法日、未知实体 | toolspec声明run_sql；Service仅做字符串正则并忽略未知键 | 声明与执行白名单同时关闭SQL，严格类型/日历/实体/范围检查 | free_sql和illegal_parameters，red.txt失败→green.txt通过；forged-* HTTP |
| 模型把真实订单数写成营业额仍获通过 | 错误数字本身确实来自真实工具结果，说明“数字集合出现”不是语义校验 | live._allowed_numbers同时接受问题数字、参数、其他指标 | 数据最终输出仅选择实际call_id与指标，data_answer按字段生成文本；拒绝任意数值散文与伪造引用 | arbitrary_prose、data_answer_binds_metric、forged_fields；替换库手算80元/120元/150% |
| trace只有截断消息、没有完整工具结果 | 超4000字请求/响应探针直接核对末尾；检查实际tool trace | llm._preview与live工具trace缺result | 完整独立请求快照、原始响应/usage与工具结果，凭证脱敏 | trace_keeps_complete、model_error_echo与HTTP trace |
| 重试预算从配置超时扣减而非实际耗时；持续空行可延长连接 | 短暂503后可用时间检查，真实HTTP空行滴流对照 | retry使用budget-per_call，HTTP单次read超时不等于总期限 | 单调时钟扣实际耗时，asyncio总deadline包围整段HTTP响应 | retry_uses_actual_elapsed_budget、keepalive单元和/ api/chat端到端normal/slow/budget补证 |
| 首次免费预检无出站请求 | health已live；trace显示socksio缺失，排除Key和模型配置 | httpx继承了本机SOCKS环境，安装依赖不包含socksio | 显式BASE_URL直连，不继承隐式代理；说明写入LLM_SETUP | preflight-first原报告保留；后续13PASS/1SKIP，P14另做合法协议端到端补证 |

修复属于G3-01实现提交（位于3686878之后）。纯数据字段绑定不声称验证G3-02/03文档事实或混合推导；没有修改公开评分器或以新mock规则抬分。

### G3-01 真实样本发现的协议缺口

首条真实模型测试固定f991720，正确查询出S02/P06六月417份，却把最终JSON的call_id写成query_metrics，触发严格拒答。不是工具结果错，也不是数值计算错；原tool消息content只有结果，服务商分配的id仅在协议字段中。真实失败见live/chat-1.json，2次API均有usage；红灯探针test_tool_result_exposes_actual_call_reference在b555bdb前失败（KeyError call_id），修复后17项通过。修复将call_id显式放入tool content并在提示中要求逐字复制，仍拒绝工具名、未知ID和自行提供的数值。费用记录保留失败调用，不删除失败样本挑结果。

### G3-01 自审：模型澄清类型

自审发现无工具时模型发出的澄清JSON会被当作自由文字refusal展示。新增test_model_can_return_structured_clarification_without_data先失败（clarify-red.txt），再支持严格的clarify/refusal终结结构；不携带未经查询的数字，也不新增追问继承。最终20项通过。真实两样本的调用ID修复与业务数值在354f6d4已验证；这次增加缺项澄清格式，不声称重新验证真实模型的澄清语义。
