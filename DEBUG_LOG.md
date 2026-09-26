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
