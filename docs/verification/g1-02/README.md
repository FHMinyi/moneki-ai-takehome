# G1-02 验收证据

固定点：5b21ee3588c1cf3f6e8bea32f2dab4b6d22768d9。
后端修复 8fa078c，前端实现 54f327c；所有验证发生在提交整理前的对应工作树。

| 证据 | 含义 |
|---|---|
| fixture-first-run.txt / before.txt | 首次夹具类型错误、修正夹具后的真实修复前 14 失败 |
| after.txt | 后端 49 passed，手算、多商品去重、退款、零金额、边界和现有工具回归 |
| independent-api.json / audit_api.py | 原始 CSV 独立计算与实际 API，8/8 一致 |
| public-metrics.txt / public-metrics/ | 官方评测器 M01–M06，6/6；不是全量评测 |
| build-first-run.txt / build.txt | Node 类型缺失与最终生产构建通过 |
| browser-first-run.txt / browser.txt | 初轮控件定位问题，最终 11 项通过 |
| select-before.txt | 诊断运行实际通过，名称中的 before 不表示失败 |
| summary-1280/1440/390.png | FastAPI 8002 同源页面与真实单日单店 API 一致 |
| loading/failure/refund-only/concurrency.png | 受控响应下的反馈和过时响应隔离 |
| invalid-date.png | 无效/倒置条件明确提示，不作为新条件提交 |
| dev-proxy.txt / dev-proxy/ | Vite 5174 代理 8002，真实 Chromium 1 项通过；截图等待刷新完成 |
| g1-01-regression/ | 本次 G1-01 台账回归截图，未覆盖原证据 |
| health.json / stores.json | 实际 mock 服务健康信息和维表返回 |
| preservation.json | 103 个原始数据、知识库、既有基线/证据文件逐字节一致 |

运行说明和03/04接入约定见 `frontend/README.md`。没有执行全量问答、真实模型或部署。
服务验收期间保留，均只绑定 localhost：
- FastAPI PID 39917，8002；cwd 仓库根目录，VAR_DIR=/tmp/moneki-g1-02-var。
- Vite PID 40797，5174；cwd 仓库 frontend 目录，API_PROXY_TARGET=http://127.0.0.1:8002。

停止前先用 `lsof -nP -iTCP:8002 -iTCP:5174 -sTCP:LISTEN` 核对 PID 仍属于这些服务，
再 `kill -TERM 39917 40797`。不要按模糊进程名杀死其他服务。
