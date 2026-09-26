import { useEffect, useState } from 'react';
import { Alert, Button, Card, Empty, Input, Select, Skeleton, Tag } from 'antd';
import { filterError, metricsUrl, parseStores, parseSummary, useDashboardRequest } from './dashboardApi';
import type { DashboardFilters, Store } from './dashboardApi';
import { TopProducts } from './TopProducts';

type Period = { start: string | null; end: string | null };
const money = (value: number) => `¥${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fields = [
  ['net_revenue', '净营业额', '销售实收减去退款'],
  ['refund_amount', '退款金额', '按退款发生日期归属'],
  ['orders', '有效订单数', '销售行按订单号去重'],
  ['aov', '客单价', '净营业额 ÷ 有效订单数'],
  ['qty', '销量', '销售数量减去退款数量'],
] as const;

export function DashboardFilter({ initial, stores, onApply }: { initial: DashboardFilters; stores: Store[]; onApply: (next: DashboardFilters) => void }) {
  const [draft, setDraft] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  return <Card className="filter-card">
    <form className="filter-form" onSubmit={event => {
      event.preventDefault();
      const problem = filterError(draft);
      setError(problem);
      if (!problem) onApply({ ...draft });
    }}>
      <label>开始日期<Input aria-label="开始日期" value={draft.start} placeholder="YYYY-MM-DD" onChange={event => setDraft({ ...draft, start: event.target.value })} /></label>
      <label>结束日期<Input aria-label="结束日期" value={draft.end} placeholder="YYYY-MM-DD" onChange={event => setDraft({ ...draft, end: event.target.value })} /></label>
      <label className="store-filter">门店<Select aria-label="门店" value={draft.store_id || ''} onChange={value => setDraft({ ...draft, store_id: value || null })} options={[{ value: '', label: '全部门店' }, ...stores.map(store => ({ value: store.store_id, label: `${store.store_name} · ${store.store_id}` }))]} /></label>
      <Button type="primary" htmlType="submit">查询汇总</Button>
    </form>
    {error && <Alert className="filter-error" type="error" showIcon message={error} description="条件未生效；下方仍为上次已生效条件的结果。" />}
    <p className="filter-help">起止日期均包含当天；编辑后点击查询，使条件生效。</p>
  </Card>;
}

export function SummaryPanel({ filters }: { filters: DashboardFilters }) {
  const [revision, setRevision] = useState(0);
  const state = useDashboardRequest(metricsUrl('/api/metrics/summary', filters), parseSummary, revision);
  return <section aria-label="经营汇总" aria-busy={state.kind === 'loading'} aria-live="polite">
    {state.kind === 'loading' && <Card><p role="status">正在读取经营汇总…</p><Skeleton active /></Card>}
    {state.kind === 'error' && <Alert type="error" showIcon message="经营汇总加载失败" description={state.message} action={<Button onClick={() => setRevision(x => x + 1)}>重试汇总</Button>} />}
    {state.kind === 'ready' && <>
      {state.data.orders === 0 && state.data.refund_amount === 0 && state.data.qty === 0 && state.data.net_revenue === 0 && <Card className="empty-card"><Empty description="该条件下暂无经营数据" /></Card>}
      <div className="summary-grid">{fields.map(([key, label, description]) => <Card key={key} className={key === 'net_revenue' ? 'kept-card' : ''}>
        <span className="stat-label">{label}</span><div className="summary-value" data-testid={`metric-${key}`}>{state.data[key] === null ? '—' : key === 'orders' || key === 'qty' ? state.data[key].toLocaleString('en-US') : money(state.data[key])}</div>
        <p>{key === 'aov' && state.data.aov === null ? '无有效订单，无可计算值' : description}</p>
      </Card>)}</div>
    </>}
  </section>;
}

/** Sole owner of applied filters for summary and future sibling visualizations. */
export function Dashboard({ period }: { period: Period }) {
  const [filters, setFilters] = useState<DashboardFilters | null>(null);
  const [revision, setRevision] = useState(0);
  const stores = useDashboardRequest('/api/stores', parseStores, revision);
  useEffect(() => {
    if (period.start && period.end) setFilters(current => current || { start: period.start!, end: period.end!, store_id: null });
  }, [period.start, period.end]);
  return <div className="dashboard">
    <div className="section-heading"><h2>经营汇总</h2><Tag>日期闭区间</Tag></div>
    {stores.kind === 'loading' && <p role="status">正在读取门店选项…</p>}
    {stores.kind === 'error' && <Alert type="error" message="门店加载失败" description={stores.message} action={<Button onClick={() => setRevision(x => x + 1)}>重试门店</Button>} />}
    {!filters && <Empty description="暂无有效数据日期，请导入数据并重建。" />}
    {filters && stores.kind === 'ready' && <>
      <DashboardFilter initial={filters} stores={stores.data} onApply={setFilters} />
      <p className="scope-note" data-testid="applied-filters">已生效：{filters.start} 至 {filters.end} · {filters.store_id ? `${stores.data.find(s => s.store_id === filters.store_id)?.store_name || ''} · ${filters.store_id}` : '全部门店'}</p>
      <SummaryPanel filters={filters} />
      <TopProducts filters={filters} />
    </>}
  </div>;
}
