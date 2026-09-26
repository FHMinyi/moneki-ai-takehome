# G1-02 经营汇总接入

`Dashboard.tsx` 中的 `Dashboard` 是经营看板生效筛选的唯一所有者。
`DashboardFilters` 在 `src/dashboardApi.ts` 导出：

```ts
type DashboardFilters = Readonly<{
  start: string;           // YYYY-MM-DD，闭区间
  end: string;
  store_id: string | null; // null = 全部门店
}>;
```

- 初始值来自 `/api/data_quality` 的清洗后 `data_period`，没有硬编码日期。
- `DashboardFilter` 只管理编辑草稿；通过日期校验后 `onApply` 一次性替换整份生效值。
- 日期/门店之外暂不增加筛选 UI；API 的 `product_id` 能力保留。
- `SummaryPanel` 仅接收 `filters`。G1-03/04 应在 Dashboard 内作为它的同级组件，接收同一份 `filters`，不自行初始化日期/门店，不与聊天会话混用。
- 公共请求边界：`metricsUrl(path, filters)` 生成相同参数；`useDashboardRequest(url, stableParser, revision?)` 提供 loading/error/ready、15 秒超时、取消与过时响应忽略。解析器放模块顶层以保持引用稳定；error 状态有 `message`，ready 状态有 `data`。组件可通过 revision 重试。
- 当前只建立了汇总所需结构，没有预建趋势/排行端点或大框架。未来新端点沿用筛选参数与自有响应解析器即可。
- `/api/stores` 返回 `{stores:[{store_id,store_name,category,district}]}`，来源为清洗库真实维表。界面使用名称与编号，不硬编码选项。
- 空区间显示 0，`aov: null` 显示“— / 无有效订单，无可计算值”；只有退款的区间可显示负净营业额/负销量，不能显示为空。
- 日期输入为明确 YYYY-MM-DD 的 AntD Input；无效或倒置条件不提交，显示反馈并标明下方仍为上次生效结果。
- 质量面板独立刷新，不因筛选重新核算；刷新质量时保留已生效看板条件。服务重建需重启，重新载入页面会取新的默认日期。

## 运行

根目录先 `npm --prefix frontend ci`，再 `npm --prefix frontend run build`。
生产资源由 FastAPI 同源挂载，需先构建再启动后端。
隔离本次验收的命令（无模型环境）：

```bash
env -u LLM_API_KEY -u LLM_BASE_URL -u LLM_MODEL \
  VAR_DIR=/tmp/moneki-g1-02-var PYTHONPATH=starter \
  starter/.venv/bin/uvicorn kbqa.server:app --host 127.0.0.1 --port 8002
```

开发代理默认后端 8000；多任务隔离可覆盖为 8002：

```bash
cd frontend
API_PROXY_TARGET=http://127.0.0.1:8002 npm run dev -- --port 5174 --strictPort
```

不要读取 `.env.live`；服务仅缺失清洗库时创建隔离产物，本任务未主动重建索引。

## 验证命令

```bash
# 仓库根目录
env -u LLM_API_KEY -u LLM_BASE_URL -u LLM_MODEL starter/.venv/bin/pytest starter/tests -q
npm --prefix frontend run build
python3 docs/verification/g1-02/audit_api.py
python3 eval/run_eval.py --base-url http://127.0.0.1:8002 \
  --questions eval/public_questions.jsonl --only metrics --out /tmp/g1-02-public-metrics
# frontend 目录；新输出放 /tmp，保留历史证据
EVIDENCE_DIR=/tmp/g1-02-quality METRICS_EVIDENCE_DIR=/tmp/g1-02-summary \
  BROWSER_BASE_URL=http://127.0.0.1:8002 npm run test:browser
```

本任务证据见 `../docs/verification/g1-02/`，调试过程见根目录 `DEBUG_LOG.md`。
浏览器的退款专属/失败/并发条件是受控注入，普通日期门店筛选调用真实 API。
