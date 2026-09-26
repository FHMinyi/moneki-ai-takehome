import { test, expect } from '@playwright/test';
const mode = process.env.DELIVERY_CASE || 'original';
const out = process.env.DELIVERY_OUTPUT!;
const money = (n: number) => `¥${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
for (const width of [1280, 1440, 390]) {
  test(`delivery ${mode} at ${width}`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 1000 });
    const errors: string[] = [], calls: string[] = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => { if (new URL(r.url()).pathname.startsWith('/api/')) calls.push(r.url()); });
    page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
    await page.goto('/');
    await expect(page.getByTestId('kept')).toHaveText(mode === 'original' ? '18,290行' : mode === 'empty' ? '0行' : '5行');
    if (mode === 'empty') {
      await expect(page.getByText('暂无有效数据日期，请导入数据并重建。')).toBeVisible();
      await expect(page.getByTestId('metric-net_revenue')).toHaveCount(0);
      expect(calls.some(u => u.includes('/api/metrics/'))).toBe(false);
    } else {
      const replacement = mode === 'replacement';
      await expect(page.getByTestId('metric-net_revenue')).toBeVisible();
      await expect(page.getByTestId('daily-selected')).toBeVisible();
      const start = replacement ? '2027-01-02' : '2026-06-08';
      const end = replacement ? '2027-01-05' : '2026-06-12';
      const id = replacement ? 'X11' : 'S03';
      if (replacement) {
        await expect(page.getByTestId('applied-filters')).toContainText(`${start} 至 ${end}`);
        await expect(page.getByTestId('metric-net_revenue')).toHaveText('¥52.02');
        await expect(page.getByRole('region', { name: '商品排行' })).toContainText('限定新点心');
        await expect(page.getByRole('region', { name: '商品排行' }).getByRole('row')).toHaveCount(4);
      }
      await page.screenshot({ path: `${out}/${mode}-initial-${width}.png`, fullPage: true });
      const stores = (await (await request.get('/api/stores')).json()).stores;
      const store = stores.find((s: {store_id: string}) => s.store_id === id);
      await page.getByRole('textbox', { name: '开始日期' }).fill(start);
      await page.getByRole('textbox', { name: '结束日期' }).fill(end);
      await page.getByRole('combobox', { name: '门店' }).press('ArrowDown');
      await page.getByTitle(`${store.store_name} · ${id}`, {exact: true}).click();
      calls.length = 0;
      await page.getByRole('button', { name: '查询汇总' }).click();
      const params = new URLSearchParams({start, end, store_id: id});
      const summary = await (await request.get(`/api/metrics/summary?${params}`)).json();
      const daily = await (await request.get(`/api/metrics/daily?${params}`)).json();
      const ranking = await (await request.get(`/api/metrics/top-products?${params}`)).json();
      await expect(page.getByTestId('metric-net_revenue')).toHaveText(money(summary.net_revenue));
      await expect(page.getByTestId('daily-selected')).toContainText(end);
      await expect(page.getByRole('region', { name: '商品排行' }).getByRole('row')).toHaveCount(ranking.products.length + 1);
      await expect.poll(() => calls.filter(u => u.includes('/api/metrics/')).length).toBe(3);
      for (const raw of calls.filter(u => u.includes('/api/metrics/'))) {
        const url = new URL(raw);
        expect(Object.fromEntries(url.searchParams)).toEqual({start, end, store_id: id});
      }
      expect(Math.round(daily.days.reduce((v:number, d:{net_revenue:number}) => v+d.net_revenue,0)*100)).toBe(Math.round(summary.net_revenue*100));
      await page.locator('.daily-details summary').click();
      const rows = page.locator('.daily-details tbody tr');
      await expect(rows).toHaveCount(daily.days.length);
      for (const [i, day] of daily.days.entries()) await expect(rows.nth(i)).toContainText(money(day.net_revenue));
      for (const product of ranking.products) {
        const row = page.getByRole('region', {name: '商品排行'}).getByRole('row').filter({hasText: product.product_id});
        await expect(row).toContainText(product.product_name);
        await expect(row).toContainText(money(product.net_revenue));
      }
      if (replacement) {
        await expect(page.getByTestId('metric-net_revenue')).toHaveText('¥22.00');
        await expect(page.getByTestId('metric-orders')).toHaveText('1');
        await expect(page.getByTestId('metric-qty')).toHaveText('2');
      }
      if (width === 390) {
        const table = page.locator('.top-products .ant-table-content');
        expect(await table.evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
        await table.evaluate(el => {el.scrollLeft=el.scrollWidth;});
        expect(await table.evaluate(el => el.scrollLeft)).toBeGreaterThan(0);
      }
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(calls.some(u => u.includes('/api/chat') || u.includes('/api/retrieve'))).toBe(false);
    expect(errors).toEqual([]);
    await page.screenshot({ path: `${out}/${mode}-${width}.png`, fullPage: true, animations: 'disabled' });
  });
}
