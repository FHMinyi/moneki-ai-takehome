import { test, expect } from '@playwright/test';

const evidence = process.env.G1_UI_EVIDENCE_DIR || '../docs/verification/g1-ui/after';

for (const width of [1280, 1440, 390]) {
  test(`real API full and short range at ${width}`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 1000 });
    const period = (await (await request.get('/api/health')).json()).data_period;
    await page.goto('/');
    await expect(page.getByTestId('metric-net_revenue')).toBeVisible();
    await expect(page.getByTestId('daily-selected')).toBeVisible();
    await expect(page.getByTestId('applied-filters')).toContainText(`${period.start} 至 ${period.end}`);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await page.locator('.daily-chart-scroll').evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
    await page.screenshot({ path: `${evidence}/full-${width}.png`, fullPage: true, animations: 'disabled' });

    await page.getByRole('textbox', { name: '开始日期' }).fill('2026-06-08');
    await page.getByRole('textbox', { name: '结束日期' }).fill('2026-06-12');
    await page.getByRole('combobox', { name: '门店' }).press('ArrowDown');
    await page.getByTitle(/· S03$/).click();
    await page.getByRole('button', { name: '查询汇总' }).click();
    await expect(page.getByTestId('applied-filters')).toContainText('2026-06-08 至 2026-06-12');
    const params = '?start=2026-06-08&end=2026-06-12&store_id=S03';
    const [summary, daily, ranking] = await Promise.all([
      request.get(`/api/metrics/summary${params}`).then(response => response.json()),
      request.get(`/api/metrics/daily${params}`).then(response => response.json()),
      request.get(`/api/metrics/top-products${params}`).then(response => response.json()),
    ]);
    const money = (n: number) => `¥${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    await expect(page.getByTestId('metric-net_revenue')).toHaveText(money(summary.net_revenue));
    await expect(page.getByTestId('daily-selected')).toContainText(daily.days.at(-1).date);
    await expect(page.getByRole('region', { name: '商品排行' }).getByRole('row')).toHaveCount(ranking.products.length + 1);
    await expect(page.getByTestId('kept')).toHaveText('18,290行');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const chart = page.locator('.daily-chart-scroll');
    await expect.poll(() => chart.evaluate(el => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(2);
    await page.screenshot({ path: `${evidence}/short-${width}.png`, fullPage: true, animations: 'disabled' });
    const firstDay = page.getByRole('button', { name: `2026-06-08 净营业额 ${money(daily.days[0].net_revenue)}` });
    await firstDay.focus();
    await firstDay.press('Tab');
    const nextDay = page.getByRole('button', { name: `2026-06-09 净营业额 ${money(daily.days[1].net_revenue)}` });
    await expect(nextDay).toBeFocused();
    expect(await nextDay.evaluate(el => getComputedStyle(el).strokeWidth)).toBe('3px');
    await nextDay.press('Shift+Tab');
    await expect(firstDay).toBeFocused();
    await firstDay.press('Enter');
    await expect(page.getByTestId('daily-selected')).toContainText('2026-06-08');
    await page.locator('.daily-details summary').click();
    await expect(page.locator('.daily-details tbody tr')).toHaveCount(daily.days.length);
    if (width === 390) {
      expect(await page.locator('.top-products .ant-table-content').evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
      expect(await page.locator('.ledger .ant-table-content').evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
    }
  });
}
