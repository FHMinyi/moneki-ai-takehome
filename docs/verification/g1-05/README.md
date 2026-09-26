# G1-05 正式验收记录

结论：第一关交付验收通过。Review fixed point：`839ec491cc80dbd79f677bf045446e2e4adfc254`，包含 PR #11 的视觉精修。
实际被测源码：`6d42e85a2d4e52cb1841e51cd67d855ab519dde2`；入口提交 `e842093`，缓存分发修复 `6d42e85`。
其后的提交只整理文档与验收材料，不修改看板、指标或启动行为。规格：[Issue #5](https://github.com/FHMinyi/moneki-ai-takehome/issues/5)。

## 环境与干净源码

2026-09-27，macOS 26.7 arm64，Python 3.12.14、Node 24.19.0、npm 12.0.2、GNU Make 3.81；详见 [environment.json](environment.json)。
从被测提交 `git archive` 到 `/tmp/moneki-g1-05-4r7gvnd1/source`，这是一次性源码导出，不是 Git 工作树。
[preflight.json](preflight.json)记录安装前不存在以下路径：
`starter/.venv`、`frontend/node_modules`、`frontend/dist`、`starter/var`、`starter/.cache`、根与 starter 的 `.env.live`。
无已安装运行环境复制；pip/npm 下载缓存可用，实际创建了新 venv 并执行 `npm ci`。
安装日志见 [setup.txt](setup.txt)，Python 实装版本见 [python-dependencies.txt](python-dependencies.txt)。

进入导出根目录实际执行的 README 三步：

```bash
env -u LLM_API_KEY -u LLM_BASE_URL -u LLM_MODEL make setup
env -u LLM_API_KEY -u LLM_BASE_URL -u LLM_MODEL make rebuild
make run PORT=8015
```

根 Makefile 的 rebuild/run 内部也清除三个模型变量。验证进程还清除了外部 DATA_DIR/KB_DIR/VAR_DIR/TODAY，
未读取 `.env.live`，无真实模型或假上游服务，健康结果是 `mock`。浏览器真实验收断言未请求 `/api/chat` 或 `/api/retrieve`。
[generated-artifacts.json](generated-artifacts.json)保存清洗库、现场生成索引和前端生产资源的大小与 SHA-256；产物本身不入库。

首次尝试在 `e842093` 导出源码时，缺失断言实际失败：仓库仍跟踪预生成 `starter/.cache/index.json`，见 [clean-export-before.txt](clean-export-before.txt)。
该次在安装前停止。提交 `6d42e85` 取消跟踪（本地文件保留并忽略），重新导出后才开始正式三步验收。
没有用删掉副本文件的办法掩盖源码携带缓存的问题，没有补造红绿提交。

## 验收矩阵

| 门槛 | 结果与证据 |
| --- | --- |
| 干净依赖安装、生产构建、同源页面 | PASS；[安装](setup.txt)、[原始重建](rebuild-original.txt)、[产物](generated-artifacts.json)；生产 HTML/资源由 FastAPI 提供 |
| 后端清洗、指标、边界、只读等回归 | **53 passed**；[backend-tests.txt](backend-tests.txt)。检索在旧测试中有固定夹具，不能据此说 RAG 正确 |
| 类型检查 | PASS；[typecheck.txt](typecheck.txt)，生产 build 本身也包含 TypeScript 检查 |
| 原始公开 metrics | **M01–M06 6/6**；[输出](metrics.txt)、[JSON](metrics/report.json)、[Markdown](metrics/report.md)。六分制阶段检查，无全量/真实模型重评 |
| 原始健康清洗字段 | 18,628 输入、18,290 保留（18,196 销售/94 退款）、338 剔除；六类 8/150/30/10/40/100，日期 2026-05-01～2026-08-31；[响应](original-health-quality.json) |
| 原始浏览器回归与本轮真实检查 | **26 passed**（已有 23 + 本轮 3）；[browser-original.txt](browser-original.txt)。全部使用新安装依赖、Chromium 和生产同源资源 |
| 同结构替换数据 | 重建、重启后 API 手算与三种宽度浏览器一致；[重建](rebuild-replacement.txt)、[API](audit-replacement.json)、[浏览器 3 passed](browser-replacement.txt) |
| 全空销售 | 重建/启动成功；API 零值/null、daily 四天补零、Top 10 空；真实页面明确显示无数据日期、零台账；[API](audit-empty.json)、[浏览器 3 passed](browser-empty.txt) |
| 版本与保护 | 导出后 266 个已跟踪文件仍与被测 commit 逐字节一致；[tested-tree.json](tested-tree.json)。主 checkout 187 个受保护文件 SHA-256 前后相同；[preservation.json](preservation.json) |

构建中的 Ant Design `use client` 与大 chunk 提示、测试中的 Starlette/httpx 弃用提示没有阻断上述运行。
N01 整题不是本关门槛：实际健康 `kb_docs=36` 仍不等于进入索引文档数，未据此扩修 RAG。
首次真实生成索引为 72 chunks，旧基线有缓存时为 53；不把这个变化称为检索修复或成绩提升。

## 独立替换夹具及手算

[fixture.py](fixture.py)只允许写入新的仓库外目录，读取源库 DDL 建相同三表，同时导出对应 CSV。
原始数据未改。替换门店为 X11「替换·河畔店」、X22「替换·山麓店」，商品为 Y91/Y92/Y93 三个新名称，日期变为 2027-01-02～2027-01-05。
故意把建档价设为 999，与实际 amount 不同，避免按单价反算蒙混通过。

11 行原始明细：5 行保留（3 条销售、1 条退款、1 条零额）；6 条分别命中六项剔除规则，含规范化后的重复行。
合法明细中订单 A 在 1 月 2 日包含两个商品 20.01 + 5.00；订单 B 在 1 月 4 日 30.02；A 在 1 月 5 日退款 3.01。
独立预期写在 [audit_fixture.py](audit_fixture.py)，不导入生产计算函数：

| 条件 | 净额 | 退款 | 订单 | 客单价 | 销量 | 每日净额（2/3/4/5 日） |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 全部门店 | 52.02 | 3.01 | 2 | 26.01 | 5 | 25.01 / 0 / 30.02 / -3.01 |
| X11 | 22.00 | 3.01 | 1 | 22.00 | 2 | 25.01 / 0 / 0 / -3.01 |
| X22 | 30.02 | 0 | 1 | 30.02 | 3 | 0 / 0 / 30.02 / 0 |

全部门店商品净额排序为 Y93 30.02、Y91 17.00、Y92 5.00。X22 的零额 Y92 明细仍存在，排行金额/销量为 0。
替换输入和空输入分别写在临时目录的 `replacement-data/`、`empty-data/`，输出分别在 `replacement-var/`、`empty-var/`。
执行 `make rebuild DATA_DIR=<绝对输入路径> VAR_DIR=<绝对产物路径>`，再用同样配置 `make run PORT=8016/8017`，
每组在启动和验收后核对输入 SHA-256 不变。没有通过改响应、改原题或覆盖仓库样本制造成功。

## 浏览器与截图

[delivery.spec.ts](delivery.spec.ts)额外覆盖每种数据的 1280/1440/390；
原始/替换页面实际操作日期和门店，核对三个接口同一条件、趋势金额之和等于汇总、逐日明细及商品名称/编号/金额、390 表格实际滚动、整页不横向溢出。
原始全套既有用例还覆盖长趋势局部滚动、键盘选日、加载/错误/重试/空态、退款负值和过期请求。
后者部分用例是明确受控响应；本轮新增九个验收用例以及下列最终截图均为真实服务数据。
新增用例监听 console error、pageerror、HTTP ≥400，结果均为空。所有旧用例截图由环境变量定向到临时目录，没有覆盖旧证据。

| 数据/条件 | 1280 | 1440 | 390 |
| --- | --- | --- | --- |
| 原始·完整区间 | [截图](screenshots/original-initial-1280.png) | [截图](screenshots/original-initial-1440.png) | [截图](screenshots/original-initial-390.png) |
| 原始·S03 六月 8–12 日 | [截图](screenshots/original-1280.png) | [截图](screenshots/original-1440.png) | [截图](screenshots/original-390.png) |
| 替换·全部门店 | [截图](screenshots/replacement-initial-1280.png) | [截图](screenshots/replacement-initial-1440.png) | [截图](screenshots/replacement-initial-390.png) |
| 替换·X11 | [截图](screenshots/replacement-1280.png) | [截图](screenshots/replacement-1440.png) | [截图](screenshots/replacement-390.png) |
| 空销售 | [截图](screenshots/empty-1280.png) | [截图](screenshots/empty-1440.png) | [截图](screenshots/empty-390.png) |

390 的筛选后截图有意将商品表滚至右侧，显示金额和销量；初始图保留左侧名称/编号。整体视觉沿用 #10，没有做样式重写。

## 复现与临时服务

从包含本证据目录的仓库根目录运行，需空闲 8015/8016/8017 端口：

```bash
python3.12 docs/verification/g1-05/verify_delivery.py --commit 6d42e85a2d4e52cb1841e51cd67d855ab519dde2
```

脚本默认新建 `/tmp` 导出目录，完成三步、后端/类型/指标/浏览器、两次输入替换，退出时停止自己创建的所有服务。
`--keep-original` 可仅保留最后恢复的原始数据 8015 服务。脚本不清除临时输出，失败也可检查日志。
本次在脚本整理期间先单独完成导出、setup、rebuild，然后实际以
`--prepared /tmp/moneki-g1-05-4r7gvnd1 --keep-original` 继续；[commands.json](commands.json)合并记录这两段准确命令，
[verification.txt](verification.txt)与 [result.json](result.json)记录后续全链路完成。

应用源码始终为 `6d42e85`；仅将本目录浏览器验收文件复制为导出目录 `frontend/tests/g1-05-delivery.spec.ts`，
该验证附加文件 SHA-256 见 `tested-tree.json`，未覆盖任何应用文件。证据文档提交不是假定的未来被测版本。

浏览器回归单独复现：服务运行后从源码根目录执行
`BROWSER_BASE_URL=http://127.0.0.1:8015 sh docs/verification/g1-05/run_browser.sh`；首次需下载 Playwright Chromium。
如果要运行新增用例，先复制 `delivery.spec.ts` 到 `frontend/tests/g1-05-delivery.spec.ts`，并设置 `DELIVERY_CASE=original` 与新的 `DELIVERY_OUTPUT=/tmp/...`。

验收完成保留服务：127.0.0.1:8015，Make 进程/进程组 55659，Uvicorn PID 55675；8016/8017 已停止。
仅等待来源主会话清理指令后停止该进程组；未操作遗留 8000/5173 或其他工作树。
临时目录 `/tmp/moneki-g1-05-4r7gvnd1` 保留安装环境、夹具和全部日志供核查；不提交这些运行环境。
源输入、知识库、两组基线、所有前序证据、未跟踪草稿与 `docs/research/` 保持原样。

## 剩余范围

未执行：最终全量/真实模型/隐藏题库、知识库替换验证、部署、手机专用设计、第二关修复。
Python 依赖尚未锁版本；复现环境记录支持排查版本漂移，但不承诺未来包源不变。正式测试平台仅上述 macOS；README 的 Linux 命令具备可移植结构，未在 Linux 实测。
