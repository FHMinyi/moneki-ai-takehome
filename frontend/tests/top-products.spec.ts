import { test, expect, type Page } from '@playwright/test';

const evidence = process.env.TOP_PRODUCTS_EVIDENCE_DIR || '../docs/verification/g1-04';
async function query(page: Page, start: string, end: string, store?: string) {
  await page.getByRole('textbox', { name: '开始日期' }).fill(start);
  await page.getByRole('textbox', { name: '结束日期' }).fill(end);
  if (store) {
    await page.getByRole('combobox', { name: '门店' }).press('ArrowDown');
    await page.getByTitle(store, { exact: true }).click();
  }
  await page.getByRole('button', { name: '查询汇总' }).click();
}

for (const width of [390, 1280, 1440]) {
  test(`real ranking and shared filter at ${width}`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 1100 });
    await page.goto('/');
    const panel = page.getByRole('region', { name: '商品排行' });
    const period = (await (await request.get('/api/health')).json()).data_period;
    const initial = (await (await request.get(`/api/metrics/top-products?start=${period.start}&end=${period.end}`)).json()).products;
    await expect(panel.getByRole('row')).toHaveCount(initial.length + 1);
    const stores = (await (await request.get('/api/stores')).json()).stores;
    const store = stores.find((s: { store_id: string }) => s.store_id === 'S02');
    await query(page, '2026-06-18', '2026-06-18', `${store.store_name} · S02`);
    const expected = (await (await request.get('/api/metrics/top-products?start=2026-06-18&end=2026-06-18&store_id=S02')).json()).products;
    await expect(page.getByTestId('applied-filters')).toContainText('S02');
    await expect(panel.getByRole('row')).toHaveCount(expected.length + 1);
    for (const [index, item] of expected.entries()) {
      const row = panel.getByRole('row').nth(index + 1);
      await expect(row).toContainText(item.product_name);
      await expect(row).toContainText(item.product_id);
      await expect(row).toContainText(`¥${item.net_revenue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
      await expect(row).toContainText(`${item.qty}`);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (width === 390) {
      await page.screenshot({ path: `${evidence}/ranking-390-left.png`, fullPage: true, animations: 'disabled' });
      const table = panel.locator('.ant-table-content');
      expect(await table.evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
      await table.scrollIntoViewIfNeeded();
      await table.evaluate(el => { el.scrollLeft = el.scrollWidth; });
      await expect(panel.getByRole('columnheader', { name: '净营业额' })).toBeInViewport();
      await expect(panel.getByRole('columnheader', { name: '销量' })).toBeInViewport();
    }
    await page.screenshot({ path: `${evidence}/ranking-${width}.png`, fullPage: true, animations: 'disabled' });
    await query(page, '2026-09-01', '2026-09-30');
    await expect(panel.getByText('该条件下暂无商品明细')).toBeVisible();
    await expect(panel.getByRole('row')).toHaveCount(0);
  });
}
