# G1-UI 视觉精修验收记录

固定点：`4615154e1d086bbf8882f73ac89a4277229ab6c0`（G1-01～04 已合并）。本阶段只调整已有经营看板的排版、色彩、层次与趋势 SVG 宽度。数据、公式、接口、排序和共同生效筛选保持原样。

## 真实页面问题与取舍

- 精修前五项经营指标等宽并列，净营业额缺少主次；质量卡片与经营卡片的视觉权重接近。精修后净营业额占更宽卡片，质量台账以分隔线和较小数字后置，但仍保留完整全量口径。
- 精修前五日趋势固定至少 620px，1440 宽容器右侧空白明显；完整区间按 38px/日形成较长滚动。精修后 SVG 以 `ResizeObserver` 铺满短区间容器，长区间以 26px/日维持可辨数据点并局部滚动。正负范围、零线、逐日数值、点击与键盘选择逻辑未变。
- 标题、辅助说明、筛选反馈、表头与金额采用统一绿色层次和等宽数字；窄屏把主指标单独成行，筛选纵排，排行与质量表仅表格局部滚动。保留未来侧栏聊天的现有主区结构，未实现聊天。

## 同条件真实 API 截图

均来自 127.0.0.1:8010 的真实清洗库和 API，`llm_mode=mock`。精修前使用 Vite 5180 代理同一 API，精修后使用 FastAPI 同源生产资源。截图中没有虚构数值。完整区间为 2026-05-01 至 2026-08-31、全部门店；短区间为 2026-06-08 至 2026-06-12、S03。

| 宽度 | 完整区间 | 短区间 |
| --- | --- | --- |
| 1280 | [前](before/full-1280.png) / [后](after/full-1280.png) | [前](before/short-1280.png) / [后](after/short-1280.png) |
| 1440 | [前](before/full-1440.png) / [后](after/full-1440.png) | [前](before/short-1440.png) / [后](after/short-1440.png) |
| 390 | [前](before/full-390.png) / [后](after/full-390.png) | [前](before/short-390.png) / [后](after/short-390.png) |

## 交互和回归

- `npm --prefix frontend run build`：TypeScript 与 Vite 生产构建通过，现有 Ant Design `use client` 和大 chunk 提示仍在。
- `BROWSER_BASE_URL=http://127.0.0.1:8010 npx playwright test --output=/tmp/moneki-g1-ui-regression-results-prod`：23/23 通过。运行时把既有测试的截图目录分别定向到 `/tmp/moneki-g1-ui-regression/{workspace,metrics,daily,ranking,integration}`，本阶段截图定向到 `docs/verification/g1-ui/after`，没有覆盖旧验收材料。
- 新增 `g1-ui.spec.ts`：三种宽度均核对真实完整/短区间、生效条件、汇总与排行结果、全量质量数值、整页无横向溢出；完整区间图表局部滚动、短区间图表铺满；390 的排行和台账局部滚动；键盘 Tab 焦点样式、Enter 选日和逐日精确明细。
- 既有集成回归：1280/390 依次切换三组真实日期/门店，检查汇总、趋势、排行请求参数同步，质量不受筛选影响。既有受控注入覆盖加载、错误、重试、空态、退款负值和过期响应；这些不是最终真实数据截图。
- Vite 开发代理上运行整套回归时，既有集成用例对质量请求数的断言曾收到 2 而非 1；生产同源资源上重跑全部 23 项通过，未降低断言。开发服务器下该计数仍待单独定位，不影响生产资源验收结论。

后端以清除 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 的环境启动，隔离 `VAR_DIR=/tmp/moneki-g1-ui-var`。未调用付费模型，未改旧基线、原始数据或前序验收证据。
