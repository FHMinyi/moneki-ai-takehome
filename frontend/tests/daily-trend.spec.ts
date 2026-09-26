import { test, expect, type Page } from '@playwright/test';

const evidence = process.env.DAILY_EVIDENCE_DIR || '../docs/verification/g1-03';
const money = (value: number) => `¥${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

async function apply(page: Page, start: string, end: string, store: string) {
  await page.getByRole('textbox', { name: '开始日期' }).fill(start);
  await page.getByRole('textbox', { name: '结束日期' }).fill(end);
  await page.getByRole('combobox', { name: '门店' }).press('ArrowDown');
  await page.getByTitle(store, { exact: true }).click();
  await page.getByRole('button', { name: '查询汇总' }).click();
}

for (const width of [1440, 1280, 390]) {
  test(`real daily trend and filters at ${width}`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto('/');
    await expect(page.getByTestId('daily-selected')).toBeVisible();
    const stores = (await (await request.get('/api/stores')).json()).stores;
    const store = stores.find((item: { store_id: string }) => item.store_id === 'S03');
    await apply(page, '2026-06-08', '2026-06-12', `${store.store_name} · S03`);
    const daily = await (await request.get('/api/metrics/daily?start=2026-06-08&end=2026-06-12&store_id=S03')).json();
    const summary = await (await request.get('/api/metrics/summary?start=2026-06-08&end=2026-06-12&store_id=S03')).json();
    expect(daily.days.map((day: { net_revenue: number }) => day.net_revenue)).toEqual([0, 0, 0, 0, 998]);
    expect(daily.days.reduce((total: number, day: { net_revenue: number }) => total + day.net_revenue, 0)).toBe(summary.net_revenue);
    await expect(page.getByTestId('daily-selected')).toContainText('2026-06-12');
    await page.getByRole('button', { name: '2026-06-08 净营业额 ¥0.00' }).click();
    await expect(page.getByTestId('daily-selected')).toContainText('2026-06-08');
    await expect(page.getByTestId('daily-selected')).toContainText('¥0.00');
    await page.getByText('查看每日明细（5 天）').click();
    await expect(page.locator('.daily-details tbody tr')).toHaveCount(5);
    await expect(page.locator('.daily-details tbody tr').last()).toContainText('¥998.00');
    const maxLabelY = Number(await page.locator('.daily-chart text').filter({ hasText: '¥998.00' }).getAttribute('y'));
    const maxPointY = Number(await page.locator('.daily-point').last().getAttribute('cy'));
    expect(maxLabelY - maxPointY).toBeCloseTo(4, 5);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `${evidence}/trend-${width}.png`, fullPage: true, animations: 'disabled' });
    await apply(page, '2026-06-04', '2026-06-04', `${stores.find((item: { store_id: string }) => item.store_id === 'S02').store_name} · S02`);
    const refundDay = await (await request.get('/api/metrics/daily?start=2026-06-04&end=2026-06-04&store_id=S02')).json();
    await expect(page.getByTestId('daily-selected')).toContainText(`2026-06-04${money(refundDay.days[0].net_revenue)}`);
    await expect(page.getByTestId('applied-filters')).toContainText('S02');
  });
}

test('controlled negative day remains below zero and exact value is readable', async ({ page }) => {
  await page.route('**/api/metrics/daily?**', async route => {
    if (route.request().url().includes('start=2026-09-01')) await route.fulfill({ json: { days: [
      { date: '2026-09-01', net_revenue: -3, orders: 0, aov: null },
      { date: '2026-09-02', net_revenue: 0, orders: 0, aov: null },
    ] } });
    else await route.continue();
  });
  await page.goto('/');
  await expect(page.getByTestId('daily-selected')).toBeVisible();
  await page.getByRole('textbox', { name: '开始日期' }).fill('2026-09-01');
  await page.getByRole('textbox', { name: '结束日期' }).fill('2026-09-02');
  await page.getByRole('button', { name: '查询汇总' }).click();
  await page.getByRole('button', { name: '2026-09-01 净营业额 ¥-3.00' }).click();
  await expect(page.getByTestId('daily-selected')).toContainText('¥-3.00');
  const negative = await page.locator('.daily-negative').getAttribute('cy');
  const zero = await page.locator('.daily-point:not(.daily-negative)').getAttribute('cy');
  expect(Number(negative)).toBeGreaterThan(Number(zero));
  const minLabelY = Number(await page.locator('.daily-chart text').filter({ hasText: '¥-3.00' }).getAttribute('y'));
  expect(minLabelY - Number(negative)).toBeCloseTo(4, 5);
  await page.screenshot({ path: `${evidence}/controlled-negative.png`, fullPage: true, animations: 'disabled' });
});
