import { useState } from 'react';
import { Alert, Button, Card, Skeleton } from 'antd';
import { metricsUrl, useDashboardRequest, validDate } from './dashboardApi';
import type { DashboardFilters } from './dashboardApi';
import './DailyTrend.css';

type DailyPoint = { date: string; net_revenue: number; orders: number; aov: number | null };
type DailyResponse = { days: DailyPoint[] };
const currency = (value: number) => `¥${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

function parseDaily(value: unknown): DailyResponse {
  const days = (value as DailyResponse)?.days;
  if (!Array.isArray(days) || days.length === 0 || days.some(day =>
    !day || !validDate(day.date) || !finite(day.net_revenue) ||
    !Number.isSafeInteger(day.orders) || day.orders < 0 ||
    !(day.aov === null || finite(day.aov)) || (day.orders === 0) !== (day.aov === null)
  )) throw new Error('每日趋势响应格式不完整');
  for (let i = 1; i < days.length; i++) {
    const previous = new Date(`${days[i - 1].date}T00:00:00Z`);
    previous.setUTCDate(previous.getUTCDate() + 1);
    if (days[i].date !== previous.toISOString().slice(0, 10)) throw new Error('每日趋势缺少日期或顺序有误');
  }
  return { days };
}

function TrendChart({ days, selectedDate, onSelect }: { days: DailyPoint[]; selectedDate: string; onSelect: (date: string) => void }) {
  const left = 82, right = 28, top = 24, bottom = 50, height = 270;
  const width = Math.max(620, left + right + (days.length - 1) * 38);
  const plotWidth = width - left - right, plotHeight = height - top - bottom;
  const minimum = Math.min(0, ...days.map(day => day.net_revenue));
  const maximum = Math.max(0, ...days.map(day => day.net_revenue));
  const lower = minimum < 0 ? minimum * 1.12 : 0;
  const upper = maximum > 0 ? maximum * 1.12 : 1;
  const y = (value: number) => top + (upper - value) / (upper - lower) * plotHeight;
  const x = (index: number) => days.length === 1 ? left + plotWidth / 2 : left + index * plotWidth / (days.length - 1);
  const points = days.map((day, index) => `${x(index)},${y(day.net_revenue)}`).join(' ');
  const labelEvery = Math.max(1, Math.ceil(days.length / Math.max(2, width / 120)));
  return <div className="daily-chart-scroll" role="region" aria-label="每日净营业额图表，可横向滚动" tabIndex={0}>
    <svg className="daily-chart" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`每日净营业额，${days[0].date} 至 ${days[days.length - 1].date}`}>
      <line x1={left} x2={width - right} y1={y(0)} y2={y(0)} className="daily-zero-line" />
      <text x={left - 10} y={y(0) + 4} textAnchor="end" className="daily-axis-label">¥0</text>
      {maximum > 0 && <text x={left - 10} y={y(maximum) + 4} textAnchor="end" className="daily-axis-label">{currency(maximum)}</text>}
      {minimum < 0 && <text x={left - 10} y={y(minimum) + 4} textAnchor="end" className="daily-axis-label">{currency(minimum)}</text>}
      {days.length > 1 && <polyline points={points} className="daily-line" />}
      {days.map((day, index) => <g key={day.date}>
        {(index % labelEvery === 0 || index === days.length - 1) && <text x={x(index)} y={height - 16} textAnchor="middle" className="daily-axis-label">{day.date.slice(5)}</text>}
        <circle cx={x(index)} cy={y(day.net_revenue)} r={day.date === selectedDate ? 6 : 4} className={day.net_revenue < 0 ? 'daily-point daily-negative' : 'daily-point'} />
        <circle cx={x(index)} cy={y(day.net_revenue)} r={15} className="daily-hit" role="button" tabIndex={0}
          aria-label={`${day.date} 净营业额 ${currency(day.net_revenue)}`}
          onClick={() => onSelect(day.date)}
          onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(day.date); } }}>
          <title>{day.date} · {currency(day.net_revenue)}</title>
        </circle>
      </g>)}
    </svg>
  </div>;
}

export function DailyTrend({ filters }: { filters: DashboardFilters }) {
  const [revision, setRevision] = useState(0);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const state = useDashboardRequest(metricsUrl('/api/metrics/daily', filters), parseDaily, revision);
  const days = state.kind === 'ready' ? state.data.days : null;
  const selected = days?.find(day => day.date === selectedDate) || days?.[days.length - 1];
  return <section className="daily-trend" aria-label="每日净营业额趋势" aria-busy={state.kind === 'loading'}>
    <div className="daily-heading"><h2>每日净营业额趋势</h2><span>单位：元 · 日期按退款发生日归属</span></div>
    {state.kind === 'loading' && <Card><p role="status">正在读取每日趋势…</p><Skeleton active /></Card>}
    {state.kind === 'error' && <Alert type="error" showIcon message="每日趋势加载失败" description={state.message} action={<Button onClick={() => setRevision(x => x + 1)}>重试趋势</Button>} />}
    {days && selected && <Card className="daily-card">
      <div className="daily-selected" aria-live="polite" data-testid="daily-selected"><span>{selected.date}</span><strong className={selected.net_revenue < 0 ? 'daily-negative-value' : ''}>{currency(selected.net_revenue)}</strong><span>有效订单 {selected.orders.toLocaleString('en-US')} 单</span></div>
      <p className="daily-help">选择图上的日期读取精确金额；横向滚动可查看完整区间。</p>
      <TrendChart days={days} selectedDate={selected.date} onSelect={setSelectedDate} />
      <details className="daily-details"><summary>查看每日明细（{days.length} 天）</summary>
        <p className="daily-table-note">订单数按每天去重；跨日出现同一订单号时，区间订单数需按整个区间重新去重。客单价也需按区间净营业额与区间订单数计算。</p>
        <div className="daily-table-scroll"><table><thead><tr><th>日期</th><th>净营业额（元）</th><th>有效订单</th><th>客单价（元）</th></tr></thead>
          <tbody>{days.map(day => <tr key={day.date}><th scope="row">{day.date}</th><td>{currency(day.net_revenue)}</td><td>{day.orders}</td><td>{day.aov === null ? '—' : currency(day.aov)}</td></tr>)}</tbody>
        </table></div>
      </details>
    </Card>}
  </section>;
}
