# G1-04 商品排行验证

固定点：`513d688d9623661af77fe248145d4bdc90bf6cbe`（G1-02 合并后）。执行工作树：`/Users/minyi/.codex/worktrees/2091/moneki-ai-takehome`。本次使用只读复用的原 checkout Python 虚拟环境，前端依赖安装在本工作树 `frontend/node_modules`。清洗库是本任务专用 `/tmp/moneki-g1-04-var/clean.db`；本工作树自己的 `.cache/index.json` 不提交。原始 `data/`、`knowledge_base/`、基线未修改；服务启动时移除了全部 LLM 三项配置，`health.llm_mode=mock`。

## 修复证据

`before.txt` 是实现前运行本任务三个独立断言的结果：同额排序不稳定；零金额行被当作销售销量；默认同额的前 10 项按逆编号显示；新增 `/api/metrics/top-products` 尚为 404。测试夹具先手工写入明细与期望，再触发失败。`after.txt` 显示三例全部通过。根因是原有 `top_products` 查询只有金额降序、销量以 `is_refund=0` 包含零金额，且没有 HTTP 路由。修复在已有清洗表上按金额正负核算销量、按商品编号破同额、查询处限定前 10 项；路由沿用现有日期校验。

## 实际验收

- `independent-api.json`：`audit_api.py` 使用 SQLite 逐行累加，不调用生产聚合函数；对账 2026-06-18 S02、同日全部门店、六月 S01 及空区间四组 API。S02 同额 `P13/P14` 按编号稳定排序；空区间为零项。真实维表名称逐项核对。
- `starter/tests/test_top_products.py`：手工夹具验证同额、退款改序（`P01` 从并列第一变第二）、门店切换、维表改名、零金额销量、空区间以及 14 个匹配商品截前 10。`after.txt` 为定向结果，`pytest.txt` 为全部 Python 测试（52 passed）。
- `frontend/tests/top-products.spec.ts`：真实 Chromium 对所选 S02 的名称、编号、金额、销量逐行比较 API；390/1280/1440 宽度均检查无工作区横向溢出，并验证空区间。390 宽度还实测表格局部可横向滚动，滚动后金额和销量列进入视口。`ranking-390-left.png` 与 `ranking-390.png` 分别记录左右两侧；其他截图见同目录。
- `browser.txt`：全部 14 项浏览器回归通过。新增表格后，旧数据质量测试的全局 `.ant-table-content` 定位出现歧义；仅将该测试的行和滚动容器定位收窄到 `.ledger`，旧测试输出留在 `/tmp/g1-04-regression-quality` 和 `/tmp/g1-04-regression-summary`，不覆盖历史证据。
- `build.txt`：TypeScript 检查与 Vite 构建通过。构建仍有既有 AntD `use client` 和大 chunk 警告；没有编译错误。

复验：

```bash
env -u LLM_API_KEY -u LLM_BASE_URL -u LLM_MODEL VAR_DIR=/tmp/moneki-g1-04-var PYTHONPATH=starter /Volumes/MACPSSD/project/moneki-ai-takehome/starter/.venv/bin/uvicorn kbqa.server:app --host 127.0.0.1 --port 8004
python3 docs/verification/g1-04/audit_api.py
PYTHONPATH=starter /Volumes/MACPSSD/project/moneki-ai-takehome/starter/.venv/bin/pytest starter/tests -q
npm --prefix frontend run build
EVIDENCE_DIR=/tmp/g1-04-regression-quality METRICS_EVIDENCE_DIR=/tmp/g1-04-regression-summary TOP_PRODUCTS_EVIDENCE_DIR=../docs/verification/g1-04 BROWSER_BASE_URL=http://127.0.0.1:8004 npm --prefix frontend run test:browser
```

后续：本分支目前只以 G1-02 为基础；主会话合并 G1-03 后，须按其通知同步最新 `main` 并检查同屏挂载和受影响回归，再由主会话合并本 PR。
