import { useEffect, useState } from 'react';

/** Applied dashboard state; never shared with chat. Dates are canonical closed bounds. */
export type DashboardFilters = Readonly<{ start: string; end: string; store_id: string | null }>;
export type Summary = DashboardFilters & { product_id: string | null; net_revenue: number; refund_amount: number; orders: number; aov: number | null; qty: number };
export type Store = { store_id: string; store_name: string };
export type RequestState<T> = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; data: T };

export function metricsUrl(path: string, filters: DashboardFilters): string {
  const query = new URLSearchParams({ start: filters.start, end: filters.end });
  if (filters.store_id) query.set('store_id', filters.store_id);
  return `${path}?${query}`;
}
export function validDate(value: string): boolean {
  return /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value) && value.slice(0, 4) !== '0000' &&
    !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
}
export function filterError(filters: DashboardFilters): string | null {
  if (!validDate(filters.start) || !validDate(filters.end)) return '日期必须是有效的 YYYY-MM-DD 格式';
  return filters.start > filters.end ? '开始日期不能晚于结束日期' : null;
}
const finite = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);
export function parseSummary(value: unknown): Summary {
  const s = value as Summary;
  if (!s || !validDate(s.start) || !validDate(s.end) ||
      !(s.store_id === null || typeof s.store_id === 'string') ||
      !(s.product_id === null || typeof s.product_id === 'string') ||
      !finite(s.net_revenue) || !finite(s.refund_amount) || s.refund_amount < 0 ||
      !Number.isSafeInteger(s.orders) || s.orders < 0 || !Number.isSafeInteger(s.qty) ||
      !(s.aov === null || finite(s.aov)) || (s.orders === 0) !== (s.aov === null)) {
    throw new Error('经营汇总响应格式不完整');
  }
  return s;
}
export function parseStores(value: unknown): Store[] {
  const stores = (value as { stores?: Store[] })?.stores;
  if (!Array.isArray(stores) || stores.some(s => !s || typeof s.store_id !== 'string' || typeof s.store_name !== 'string')) {
    throw new Error('门店列表响应格式不完整');
  }
  return stores;
}
/** Reusable read boundary: latest URL wins, cleanup aborts and ignores obsolete responses. */
export function useDashboardRequest<T>(url: string | null, parse: (value: unknown) => T, revision = 0): RequestState<T> {
  const [result, setResult] = useState<{ url: string; revision: number; state: RequestState<T> }>();
  useEffect(() => {
    if (!url) return;
    let active = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    setResult({ url, revision, state: { kind: 'loading' } });
    (async () => {
      try {
        const response = await fetch(url, { signal: controller.signal });
        const data: unknown = await response.json();
        if (!response.ok) throw new Error((data as { error?: string })?.error || `服务返回 ${response.status}`);
        const parsed = parse(data);
        if (active) setResult({ url, revision, state: { kind: 'ready', data: parsed } });
      } catch (error) {
        if (active) setResult({ url, revision, state: { kind: 'error', message: controller.signal.aborted ? '请求超时，请重试' : error instanceof Error ? error.message : '读取失败' } });
      } finally { window.clearTimeout(timeout); }
    })();
    return () => { active = false; controller.abort(); window.clearTimeout(timeout); };
  }, [url, parse, revision]);
  // Do not render the previous result even during the render before effect cleanup.
  return result?.url === url && result.revision === revision ? result.state : { kind: 'loading' };
}
