import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Alert, Button, Card, ConfigProvider, Empty, Skeleton, Table, Tag } from 'antd';
import 'antd/dist/reset.css';
import './style.css';
import { Dashboard } from './Dashboard';
import { ChatSidebar } from './ChatSidebar';

type Report = { raw_rows: number; kept_rows: number; removed_rows: number; removed: Record<string, number> };
type Quality = { cleaning_report: Report; data_period: { start: string | null; end: string | null } };
type State = { kind: 'loading' } | { kind: 'error' } | { kind: 'ready'; data: Quality };
const reasons = [
  ['1_unparseable_date', '日期无法解析', '接受标准日期、斜杠日期与日在前的旧 POS 日期'],
  ['2_empty_amount', '实收金额为空', '直接剔除，不以商品单价回填'],
  ['3_qty_le_zero', '数量小于或等于 0', '按整数解析后检查数量'],
  ['4_store_not_in_stores', '门店编号无效', '先去除首尾空白并转为大写，再核对门店表'],
  ['5_product_not_in_products', '商品编号无效', '先规范化编号，再核对商品表'],
  ['6_duplicate_row', '完全重复的明细', '七个字段规范化后完全相同，只保留一行'],
] as const;
const count = (n: number) => n.toLocaleString('en-US');
function validQuality(value: unknown): value is Quality {
  if (!value || typeof value !== 'object') return false;
  const q = value as Quality;
  const r = q.cleaning_report;
  const integer = (n: unknown) => typeof n === 'number' && Number.isSafeInteger(n) && n >= 0;
  const day = (d: unknown) => d === null || (typeof d === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(d));
  return !!r && !!q.data_period && !!r.removed && integer(r.raw_rows) && integer(r.kept_rows) &&
    integer(r.removed_rows) && reasons.every(([key]) => integer(r.removed[key])) &&
    reasons.reduce((sum, [key]) => sum + r.removed[key], 0) === r.removed_rows &&
    r.raw_rows === r.kept_rows + r.removed_rows && day(q.data_period.start) && day(q.data_period.end);
}
function Workspace() {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [revision, setRevision] = useState(0);
  const [period, setPeriod] = useState<Quality['data_period'] | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    let active = true;
    setState({ kind: 'loading' });
    (async () => {
      try {
        const response = await fetch('/api/data_quality', { signal: controller.signal });
        if (!response.ok) throw new Error('Request failed');
        const data: unknown = await response.json();
        if (!validQuality(data)) throw new Error('Invalid cleaning ledger');
        if (active) { setState({ kind: 'ready', data }); setPeriod(data.data_period); }
      } catch {
        if (active) setState({ kind: 'error' });
      } finally { window.clearTimeout(timeout); }
    })();
    return () => { active = false; controller.abort(); window.clearTimeout(timeout); };
  }, [revision]);
  const report = state.kind === 'ready' ? state.data.cleaning_report : null;
  return <div className="workspace">
    <header className="brandbar"><a href="/" className="brand"><span className="brandmark">m</span>moneki<span className="brand-sub">运营工作台</span></a><span className="workspace-label">总部运营 / 经营看板</span></header>
    <main>
      <div className="page-heading"><div><div className="eyebrow">经营看板</div><h1>看清每一天的经营</h1><p>按日期和门店查看真实经营数据，核对清洗结果与指标口径。</p></div><Button onClick={() => setRevision(x => x + 1)} loading={state.kind === 'loading'}>刷新数据</Button></div>
      {period && <Dashboard period={period} />}
      <section className="quality-section" aria-label="数据质量台账">
        <div className="section-heading"><h2>数据质量</h2><Tag color="green">KB-001 · 现行口径</Tag></div>
        <p className="scope-note">全量重建结果 · 不随看板筛选变化</p>
        <div aria-live="polite" aria-busy={state.kind === 'loading'}>
        {state.kind === 'loading' && <Card><p role="status">正在读取数据质量…</p><Skeleton active paragraph={{ rows: 5 }} /></Card>}
        {state.kind === 'error' && <Alert type="error" showIcon message="数据质量加载失败" description="暂时无法读取完整台账，请确认服务已启动且已完成重建。" action={<Button onClick={() => setRevision(x => x + 1)}>重试</Button>} />}
        {state.kind === 'ready' && report && <>
          <div className="stat-grid">
            <Card><span className="stat-label">原始明细</span><div className="stat-value" data-testid="raw">{count(report.raw_rows)}<small>行</small></div><p>来自 POS 原始数据</p></Card>
            <Card className="kept-card"><span className="stat-label">有效明细</span><div className="stat-value" data-testid="kept">{count(report.kept_rows)}<small>行</small></div><p>保留合法销售与退款</p></Card>
            <Card><span className="stat-label">剔除明细</span><div className="stat-value" data-testid="removed">{count(report.removed_rows)}<small>行</small></div><p>按首个命中原因计数</p></Card>
          </div>
          <div className="period-bar"><span>有效数据日期</span><strong>{state.data.data_period.start && state.data.data_period.end ? `${state.data.data_period.start} — ${state.data.data_period.end}` : '暂无有效日期'}</strong><Tag color="green">台账已对齐</Tag></div>
          {report.kept_rows === 0 && <Card className="empty-card"><Empty description={report.raw_rows === 0 ? '暂无销售明细，请导入数据并重建。' : '暂无有效明细，请检查下方剔除原因。'} /></Card>}
          <Card className="ledger" title="剔除原因台账" extra={<span className="subtle">按执行顺序</span>}>
            <p className="table-note">每行只计入最先命中的原因，避免重复计算剔除数量。</p>
            <Table pagination={false} rowKey="key" scroll={{ x: 660 }} dataSource={reasons.map(([key, name, description], index) => ({ key, name, description, order: index + 1, rows: report.removed[key] }))} columns={[
              { title: '顺序', dataIndex: 'order', width: 72, render: value => <span className="order">{String(value).padStart(2, '0')}</span> },
              { title: '剔除原因', dataIndex: 'name', width: 180 },
              { title: '执行口径', dataIndex: 'description' },
              { title: '剔除行数', dataIndex: 'rows', width: 112, align: 'right', render: value => <strong>{count(value)}</strong> },
            ]} />
            <div className="reconciliation"><span>台账核对</span><strong>{count(report.raw_rows)} = {count(report.kept_rows)} + {count(report.removed_rows)}</strong><span>原始 = 保留 + 剔除</span></div>
          </Card>
          <p className="footnote">原始数据保持不变。重建完成后重启服务，再刷新此页查看最新结果。</p>
        </>}
        </div>
      </section>
    </main>
    <footer>MONEKI / 数据口径以《指标口径手册 v3》为准</footer>
    <ChatSidebar />
  </div>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><ConfigProvider theme={{ token: { colorPrimary: '#246b52', borderRadius: 10, fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', colorText: '#20382e', colorBorderSecondary: '#e5eae6' } }}><Workspace /></ConfigProvider></React.StrictMode>);
