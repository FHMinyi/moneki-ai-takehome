# 经营看板 + 问答服务

当前第一关完整交付请优先使用[根 README 的三步入口](../README.md)。下方 G1-01/02 段落记录阶段演进；当前页面已包含汇总、趋势和 Top 10。

运营内部用的问答服务：一条线查销售数据库，一条线查公司知识库。
Python 3.12，只用 `fastapi` / `uvicorn` / `httpx`，测试用 `pytest`。

## 跑起来

```bash
make setup      # uv venv --python 3.12 + 装依赖
make rebuild    # 重建清洗表与检索索引
make run        # 起服务，默认 http://127.0.0.1:8000
make test       # 跑测试
```

换一套数据或知识库：

```bash
make rebuild DATA_DIR=/path/to/data KB_DIR=/path/to/knowledge_base
```

`DATA_DIR`、`KB_DIR`、`VAR_DIR` 也可以直接作为环境变量传给 `make run`。

## 目录

| 文件 | 干什么的 |
|---|---|
| `kbqa/config.py` | 环境变量与路径；“今天”固定 2026-09-01 |
| `kbqa/cleaning.py` | 把原始 `sales` 导进 `var/clean.db` |
| `kbqa/tools.py` | 指标查询：汇总、按天、支付方式、商品排行、门店、品类、对比、单价 |
| `kbqa/loader.py` | 读知识库文件，认出 doc_id、标题、生效日期 |
| `kbqa/chunker.py` | 切块 |
| `kbqa/tokenizer.py` | 分词 |
| `kbqa/index.py` | BM25 索引 + 磁盘缓存 |
| `kbqa/retriever.py` | 检索与元数据过滤 |
| `kbqa/docfacts.py` / `units.py` | 从文档里挑句子、出引用 |
| `kbqa/planner.py` / `entities.py` / `timeparse.py` | 意图、实体、时间 |
| `kbqa/answerer.py` / `hybrid.py` / `render.py` | 组装回答 |
| `kbqa/llm.py` / `live.py` / `toolspec.py` | 模型客户端与工具回路 |
| `kbqa/service.py` / `server.py` | 编排与 HTTP 层 |

## 接口

| 方法 | 路径 |
|---|---|
| GET | `/api/health` |
| GET | `/api/metrics/summary` |
| GET | `/api/metrics/daily` |
| POST | `/api/retrieve` |
| POST | `/api/chat` |
| GET | `/api/trace/{trace_id}` |
| GET | `/api/data_quality` |

## 两种模式

配了 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 就走模型，没配就走本地模板回答。
没有 Key 时服务照常启动，`/api/chat` 不会 500。

交接说明见 `HANDOVER.md`。

## G1-01：数据质量工作区

前端位于仓库根目录 `frontend/`，需要 Node.js 20.19+ 或 22.12+。
从根目录安装、检查并构建：

```bash
npm --prefix frontend ci
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

先构建前端，再启动 FastAPI；它在启动时挂载 `frontend/dist/`，浏览器打开
<http://127.0.0.1:8000/>。本关只显示全量清洗质量，不提供尚未实现的指标或聊天入口。

在 `starter/` 目录执行以下命令，隔离本次产物并明确禁用真实模型：

```bash
LLM_API_KEY= LLM_BASE_URL= LLM_MODEL= VAR_DIR=var/g1-01 make rebuild
LLM_API_KEY= LLM_BASE_URL= LLM_MODEL= VAR_DIR=var/g1-01 make run
```

更换原始数据后执行同一重建命令，**重启服务**后再刷新页面。
`data/pos.db` 以 SQLite `mode=ro` 打开；清洗结果单独生成，成功写完后原子替换，
禁止把源库设为目标库。重建命令仍执行 starter 原有索引流程，本关没有修复索引缓存或文档计数。

开发模式：先在 8000 端口启动后端，再从根目录执行
`npm --prefix frontend run dev`，打开 <http://127.0.0.1:5173/>。
Vite 将 `/api` 代理到 8000；生产页面使用同源相对路径。

验证（从根目录）：

```bash
LLM_API_KEY= LLM_BASE_URL= LLM_MODEL= starter/.venv/bin/python -m pytest starter/tests -q
python3 docs/verification/g1-01/audit_sample.py
# 浏览器验证要求上面的 8000 服务正在运行，且使用提供的原始样本。
cd frontend
npx playwright install chromium
npm run test:browser
# 可选：同时启动 Vite 后核对开发代理
BROWSER_BASE_URL=http://127.0.0.1:5173 npm run test:browser -- --grep 'real API ledger at 1280px'
```

证据位于 `docs/verification/g1-01/`，调试记录见根目录 `DEBUG_LOG.md`。
浏览器正常状态使用真实 API；加载、503 和空状态使用 Playwright 的网络响应控制，
不代表原始数据为空。空数据库行为另有后端测试。
`/api/data_quality.cleaning_report.removed` 只包含六类互斥剔除原因，
新增 `removed_rows` 是这六项之和；`data_period` 从清洗表取最小/最大日期，空表为两个 `null`。

KB-001 未定义非空且非数字金额的处置：这类记录若通过前五项检查，重建明确报错并保留旧产物，
不填 0、不扩展剔除口径。零金额不属于销售或退款，但不被六条规则剔除。

## G1-02：日期/门店与经营汇总

页面增加日期闭区间、真实门店列表与五项汇总；首次默认清洗后日期范围。
API 汇总遵循 KB-001：退款自身日期、正金额订单去重、销量扣退款、Decimal 四舍五入。
无有效订单时客单价为 null；错误日期和起止倒置返回 400。商品筛选仍由 API 支持。
后续趋势/排行复用前端 `DashboardFilters` 与公共请求边界，见 [前端接入说明](../frontend/README.md)。
本次公开指标评测 M01–M06 为 6/6，仅代表指标类别，不替代全量或真实模型评测。
