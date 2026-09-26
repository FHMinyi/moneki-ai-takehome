import { test, expect } from '@playwright/test';
const evidence = process.env.EVIDENCE_DIR || '../docs/verification/g1-01';
for (const width of [1280, 1440, 390]) {
  test(`real API ledger at ${width}px`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 1000 });
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('/');
    await expect(page.getByTestId('kept')).toHaveText('18,290行');
    await expect(page.getByTestId('raw')).toHaveText('18,628行');
    await expect(page.getByTestId('removed')).toHaveText('338行');
    await expect(page.getByText('2026-05-01 — 2026-08-31')).toBeVisible();
    const q = await (await request.get('/api/data_quality')).json();
    const health = await (await request.get('/api/health')).json();
    expect(health.llm_mode).toBe('mock');
    expect(health.valid_sales_rows).toBe(q.cleaning_report.kept_rows);
    const rows = page.locator('.ledger tbody tr.ant-table-row');
    await expect(rows).toHaveCount(6);
    for (const [i, expected] of [8, 150, 30, 10, 40, 100].entries()) {
      await expect(rows.nth(i).locator('td').last()).toHaveText(String(expected));
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (width === 390) {
      const scroller = page.locator('.ledger .ant-table-content');
      expect(await scroller.evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
      await scroller.evaluate(el => { el.scrollLeft = el.scrollWidth; });
      await rows.nth(5).locator('td').last().scrollIntoViewIfNeeded();
      await expect(rows.nth(5).locator('td').last()).toBeInViewport();
      await scroller.evaluate(el => { el.scrollLeft = 0; });
    }
    await page.getByRole('button', { name: '刷新数据' }).click();
    await expect(page.getByTestId('kept')).toHaveText('18,290行');
    await expect(page.getByRole('button', { name: '刷新数据' })).toBeEnabled();
    await page.screenshot({ path: `${evidence}/workspace-${width}.png`, fullPage: true, animations: 'disabled' });
    expect(errors).toEqual([]);
  });
}

test('loading, failure and retry are visible', async ({ page }) => {
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/data_quality', async route => { await held; await route.fulfill({ status: 503, body: '{}' }); });
  await page.goto('/');
  await expect(page.getByRole('status')).toHaveText('正在读取数据质量…');
  await page.screenshot({ path: `${evidence}/loading.png`, fullPage: true });
  release();
  await expect(page.getByText('数据质量加载失败')).toBeVisible();
  await page.screenshot({ path: `${evidence}/failure.png`, fullPage: true });
  await page.unroute('**/api/data_quality');
  await page.getByRole('button', { name: /重\s*试/ }).click();
  await expect(page.getByTestId('kept')).toHaveText('18,290行');
});

test('empty ledger and rejected inconsistent response', async ({ page, request }) => {
  const actual = await (await request.get('/api/data_quality')).json();
  const empty = structuredClone(actual);
  Object.assign(empty.cleaning_report, { raw_rows: 0, kept_rows: 0, removed_rows: 0 });
  for (const key of Object.keys(empty.cleaning_report.removed)) empty.cleaning_report.removed[key] = 0;
  empty.data_period = { start: null, end: null };
  await page.route('**/api/data_quality', route => route.fulfill({ json: empty }));
  await page.goto('/');
  await expect(page.getByText('暂无销售明细，请导入数据并重建。')).toBeVisible();
  await expect(page.getByText('暂无有效日期')).toBeVisible();
  await page.screenshot({ path: `${evidence}/empty.png`, fullPage: true });
  empty.cleaning_report.kept_rows = 1;
  await page.getByRole('button', { name: '刷新数据' }).click();
  await expect(page.getByText('数据质量加载失败')).toBeVisible();
});
