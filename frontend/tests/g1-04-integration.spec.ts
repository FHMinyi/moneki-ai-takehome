import { test, expect, type Page } from '@playwright/test';

const evidence = process.env.G1_04_INTEGRATION_EVIDENCE_DIR || '../docs/verification/g1-04/integration';
const money = (value: number) => `¥${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

async function apply(page: Page, start: string, end: string, storeLabel: string) {
  await page.getByRole('textbox', { name: '开始日期' }).fill(start);
  await page.getByRole('textbox', { name: '结束日期' }).fill(end);
  await page.getByRole('combobox', { name: '门店' }).press('ArrowDown');
  await page.getByTitle(storeLabel, { exact: true }).click();
  await page.getByRole('button', { name: '查询汇总' }).click();
}

for (const width of [1280, 390]) {
  test(`summary, trend and ranking share sequential filters at ${width}`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 1100 });
    const seen: string[] = [];
    let qualityCalls = 0;
    page.on('request', call => {
      const url = new URL(call.url());
      if (['/api/metrics/summary', '/api/metrics/daily', '/api/metrics/top-products'].includes(url.pathname)) seen.push(url.toString());
      if (url.pathname === '/api/data_quality') qualityCalls++;
    });
    await page.goto('/');
    await expect(page.getByTestId('metric-net_revenue')).toBeVisible();
    await expect(page.getByTestId('daily-selected')).toBeVisible();
    const period = (await (await request.get('/api/health')).json()).data_period;
    const initial = (await (await request.get(`/api/metrics/top-products?start=${period.start}&end=${period.end}`)).json()).products;
    await expect(page.getByRole('region', { name: '商品排行' }).getByRole('row')).toHaveCount(initial.length + 1);
    const kept = await page.getByTestId('kept').textContent();
    const stores = (await (await request.get('/api/stores')).json()).stores;
    const label = (id: string) => {
      const store = stores.find((item: { store_id: string }) => item.store_id === id);
      return `${store.store_name} · ${id}`;
    };
    for (const [index, [start, end, store]] of [
      ['2026-06-18', '2026-06-18', 'S02'],
      ['2026-06-08', '2026-06-12', 'S03'],
      ['2026-06-04', '2026-06-04', 'S02'],
    ].entries()) {
      seen.length = 0;
      await apply(page, start, end, label(store));
      const params = new URLSearchParams({ start, end, store_id: store });
      const [summary, daily, ranking] = await Promise.all([
        request.get(`/api/metrics/summary?${params}`).then(response => response.json()),
        request.get(`/api/metrics/daily?${params}`).then(response => response.json()),
        request.get(`/api/metrics/top-products?${params}`).then(response => response.json()),
      ]);
      await expect(page.getByTestId('metric-net_revenue')).toHaveText(money(summary.net_revenue));
      await expect(page.getByTestId('daily-selected')).toContainText(daily.days.at(-1).date);
      await expect(page.getByRole('region', { name: '商品排行' }).getByRole('row')).toHaveCount(ranking.products.length + 1);
      await expect.poll(() => seen.length).toBe(3);
      expect(seen.map(raw => {
        const url = new URL(raw);
        return [url.pathname, url.searchParams.get('start'), url.searchParams.get('end'), url.searchParams.get('store_id')];
      }).sort()).toEqual([
        ['/api/metrics/summary', start, end, store],
        ['/api/metrics/daily', start, end, store],
        ['/api/metrics/top-products', start, end, store],
      ].sort());
      expect(Math.round(daily.days.reduce((sum: number, day: { net_revenue: number }) => sum + day.net_revenue, 0) * 100)).toBe(Math.round(summary.net_revenue * 100));
      const detail = page.locator('.daily-details');
      if (!(await detail.evaluate(el => (el as HTMLDetailsElement).open))) await detail.locator('summary').click();
      const dayRows = detail.locator('tbody tr');
      await expect(dayRows).toHaveCount(daily.days.length);
      for (const [dayIndex, day] of daily.days.entries()) await expect(dayRows.nth(dayIndex)).toContainText(money(day.net_revenue));
      const productRows = page.getByRole('region', { name: '商品排行' }).getByRole('row');
      for (const [productIndex, product] of ranking.products.entries()) {
        const row = productRows.nth(productIndex + 1);
        await expect(row).toContainText(product.product_id);
        await expect(row).toContainText(product.product_name);
        await expect(row).toContainText(money(product.net_revenue));
      }
      await expect(page.getByTestId('kept')).toHaveText(kept!);
      expect(qualityCalls).toBe(1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      if (width === 390) {
        expect(await page.locator('.daily-chart-scroll').evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
        expect(await page.locator('.top-products .ant-table-content').evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
      }
      await page.screenshot({ path: `${evidence}/combined-${width}-${index + 1}.png`, fullPage: true, animations: 'disabled' });
    }
  });
}
