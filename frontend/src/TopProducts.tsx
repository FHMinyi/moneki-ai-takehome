import { useState } from 'react';
import { Alert, Button, Card, Empty, Skeleton, Table } from 'antd';
import { metricsUrl, useDashboardRequest, validDate } from './dashboardApi';
import type { DashboardFilters } from './dashboardApi';
import './TopProducts.css';

type Product = { product_id: string; product_name: string; net_revenue: number; qty: number };
type Ranking = DashboardFilters & { products: Product[] };
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

function parseRanking(value: unknown): Ranking {
  const result = value as Ranking;
  if (!result || !validDate(result.start) || !validDate(result.end) ||
      !(result.store_id === null || typeof result.store_id === 'string') ||
      !Array.isArray(result.products) || result.products.length > 10 ||
      result.products.some(item => !item || typeof item.product_id !== 'string' ||
        typeof item.product_name !== 'string' || !finite(item.net_revenue) ||
        !Number.isSafeInteger(item.qty))) {
    throw new Error('商品排行响应格式不完整');
  }
  return result;
}

const money = (value: number) => `¥${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function TopProducts({ filters }: { filters: DashboardFilters }) {
  const [revision, setRevision] = useState(0);
  const state = useDashboardRequest(metricsUrl('/api/metrics/top-products', filters), parseRanking, revision);
  return <section className="top-products" aria-label="商品排行" aria-busy={state.kind === 'loading'} aria-live="polite">
    <div className="top-products-heading"><h2>Top 10 商品</h2><p>按净营业额降序；同额按商品编号升序。销量为销售数量减退款数量。窄屏可左右滑动表格。</p></div>
    {state.kind === 'loading' && <Card><p role="status">正在读取商品排行…</p><Skeleton active /></Card>}
    {state.kind === 'error' && <Alert type="error" showIcon message="商品排行加载失败" description={state.message} action={<Button onClick={() => setRevision(x => x + 1)}>重试排行</Button>} />}
    {state.kind === 'ready' && <Card className="top-products-card">
      {state.data.products.length === 0 ? <Empty description="该条件下暂无商品明细" /> :
        <Table<Product> rowKey="product_id" dataSource={state.data.products} pagination={false} scroll={{ x: 680 }}
          columns={[
            { title: '排名', key: 'rank', width: 76, render: (_value, _record, index) => index + 1 },
            { title: '商品名称 / 编号', key: 'product', width: 285, render: (_value, item) => <span>{item.product_name} <span className="top-products-id">{item.product_id}</span></span> },
            { title: '净营业额', dataIndex: 'net_revenue', key: 'net_revenue', align: 'right', width: 170, render: (value: number) => money(value) },
            { title: '销量', dataIndex: 'qty', key: 'qty', align: 'right', width: 120, render: (value: number) => value.toLocaleString('en-US') },
          ]} />}
    </Card>}
  </section>;
}
