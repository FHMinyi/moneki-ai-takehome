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
