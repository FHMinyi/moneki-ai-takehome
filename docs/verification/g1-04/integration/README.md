# G1-03 与 G1-04 同屏集成

- 合并基础：`origin/main` 的 `673e8484869fa210ba72fa4033dd7334d3736e3e`（G1-03 PR #9）。以正常 Git merge 保留两侧历史，不重写提交。唯一文本冲突为 `frontend/src/Dashboard.tsx` 的 import/挂载；保留汇总、每日趋势、商品排行同级并共用 `DashboardFilters`。
- `build.txt`：TypeScript 检查和 Vite 构建通过。`backend-tests.txt`：本次冲突相关的趋势与排行 Python 测试 4 项通过；后端实现无新的合并冲突。
- `browser.txt`：`frontend/tests/g1-04-integration.spec.ts` 在 1280 和 390 两种宽度各连续切换三组日期/门店：S02 单日、S03 五日、S02 另一单日。每次均核实 summary/daily/top-products 三条页面请求参数相同；UI 汇总与 API 相同，逐日净额合计等于汇总，逐日明细及排行逐项与 API 对应；数据质量台账数值不变且未因筛选重新请求。390 宽度核对趋势图与排行表各自局部横向滚动，整个页面无横向溢出。
- `combined-1280-*.png`、`combined-390-*.png`：上述每次条件切换后的真实 Chromium 全页截图，编号对应三组筛选的顺序。原 G1-04 定向测试与此前全套回归证据在上级目录，G1-03 自身证据在 `docs/verification/g1-03/`；本次只补受合并影响的组合验证。
- 服务：复用本任务隔离的 127.0.0.1:8004、PID 44244，未启动 Vite 5176；`/tmp/moneki-g1-04-var/clean.db` 与当前工作树缓存各自隔离。`health.llm_mode=mock`，没有真实模型调用。服务继续保留供主会话验收。
