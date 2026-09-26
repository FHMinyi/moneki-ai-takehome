import { test, expect, type Page } from '@playwright/test';
const evidence = process.env.METRICS_EVIDENCE_DIR || '../docs/verification/g1-02';
const formatted = (key: string, value: number | null) => value === null ? '—' : key === 'qty' || key === 'orders' ? value.toLocaleString('en-US') : `¥${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
async function query(page: Page, start: string, end: string, store?: string) {
  await page.getByRole('textbox', { name: '开始日期' }).fill(start);
  await page.getByRole('textbox', { name: '结束日期' }).fill(end);
  if (store) {
    await page.getByRole('combobox', { name: '门店' }).press('ArrowDown');
    await page.getByTitle(store, { exact: true }).click();
    await expect(page.getByRole('combobox', { name: '门店' })).toHaveAttribute('aria-expanded', 'false');
  }
  await page.getByRole('button', { name: '查询汇总' }).click();
  await expect(page.locator('.ant-select-dropdown:visible')).toHaveCount(0);
}
for (const width of [1280, 1440, 390]) {
  test(`real summary and filters at ${width}`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 1100 });
    await page.goto('/');
    await expect(page.getByTestId('applied-filters')).toContainText('2026-05-01 至 2026-08-31');
    const stores = (await (await request.get('/api/stores')).json()).stores;
    const store = stores.find(s => s.store_id === 'S02');
    await query(page, '2026-06-18', '2026-06-18', `${store.store_name} · S02`);
    const result = await (await request.get('/api/metrics/summary?start=2026-06-18&end=2026-06-18&store_id=S02')).json();
    for (const key of ['net_revenue','refund_amount','orders','aov','qty']) await expect(page.getByTestId(`metric-${key}`)).toHaveText(formatted(key, result[key]));
    await expect(page.getByTestId('applied-filters')).toContainText('S02');
    await expect(page.getByTestId('kept')).toHaveText('18,290行');
    const refreshed = page.waitForResponse(r => r.url().includes('/api/data_quality'));
    await page.getByRole('button', { name: '刷新数据' }).click();
    await refreshed;
    await expect(page.getByRole('button', { name: '刷新数据' })).toBeEnabled();
    await expect(page.getByTestId('kept')).toHaveText('18,290行');
    await expect(page.getByTestId('applied-filters')).toContainText('2026-06-18 至 2026-06-18');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `${evidence}/summary-${width}.png`, fullPage: true, animations: 'disabled' });
    await query(page, '2026-09-01','2026-09-30');
    await expect(page.getByText('该条件下暂无经营数据')).toBeVisible();
    await expect(page.getByTestId('metric-aov')).toHaveText('—');
  });
}

test('invalid dates do not submit and report unchanged applied range', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('metric-orders')).toBeVisible();
  const sent: string[] = [];
  page.on('request', r => { if (r.url().includes('/api/metrics/summary')) sent.push(r.url()); });
  await query(page,'2026-02-30','2026-06-30');
  await expect(page.getByText('日期必须是有效的 YYYY-MM-DD 格式')).toBeVisible();
  await query(page,'20260601','2026-06-30');
  await expect(page.getByText('日期必须是有效的 YYYY-MM-DD 格式')).toBeVisible();
  await query(page,'2026-07-01','2026-06-30');
  await expect(page.getByText('开始日期不能晚于结束日期')).toBeVisible();
  expect(sent).toEqual([]);
  await expect(page.getByTestId('applied-filters')).toContainText('2026-05-01 至 2026-08-31');
  await page.screenshot({ path: `${evidence}/invalid-date.png`, fullPage: true, animations: 'disabled' });
});

test('loading failure retry and refund-only display', async ({ page }) => {
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/metrics/summary?**', async route => { await held; await route.fulfill({ status:503,json:{error:'受控服务失败'} }); });
  await page.goto('/');
  await expect(page.getByText('正在读取经营汇总…')).toBeVisible();
  await page.screenshot({ path:`${evidence}/loading.png`,fullPage:true });
  release();
  await expect(page.getByText('经营汇总加载失败')).toBeVisible();
  await expect(page.getByTestId('metric-net_revenue')).toHaveCount(0);
  await page.screenshot({ path:`${evidence}/failure.png`,fullPage:true });
  await page.unroute('**/api/metrics/summary?**');
  await page.getByRole('button',{name:'重试汇总'}).click();
  await expect(page.getByTestId('metric-orders')).toBeVisible();
  await page.route('**/api/metrics/summary?**', route => route.fulfill({json:{start:'2026-06-02',end:'2026-06-02',store_id:null,product_id:null,net_revenue:-3,refund_amount:3,orders:0,aov:null,qty:-1}}));
  await query(page,'2026-06-02','2026-06-02');
  await expect(page.getByTestId('metric-net_revenue')).toHaveText('¥-3.00');
  await expect(page.getByTestId('metric-aov')).toHaveText('—');
  await expect(page.getByText('该条件下暂无经营数据')).toHaveCount(0);
  await page.screenshot({path:`${evidence}/refund-only.png`,fullPage:true});
});

test('obsolete successful response cannot overwrite newer filters', async ({ page }) => {
  // Deliberately make fetch ignore AbortSignal so the active-response guard is exercised.
  await page.addInitScript(() => {
    const original = window.fetch;
    window.fetch = (input, init) => original(input, { ...init, signal: undefined });
  });
  await page.goto('/');
  await expect(page.getByTestId('metric-orders')).toBeVisible();
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let oldStarted!: () => void;
  const started = new Promise<void>(resolve => { oldStarted = resolve; });
  await page.route('**/api/metrics/summary?**', async route => {
    if (route.request().url().includes('start=2026-06-01')) {
      const response = await route.fetch();
      oldStarted();
      await held;
      await route.fulfill({response});
    } else await route.continue();
  });
  await query(page,'2026-06-01','2026-06-30');
  await started;
  await query(page,'2026-09-01','2026-09-30');
  await expect(page.getByText('该条件下暂无经营数据')).toBeVisible();
  const oldResponse = page.waitForResponse(r => r.url().includes('start=2026-06-01'));
  release();
  await oldResponse;
  await page.waitForTimeout(150);
  await expect(page.getByTestId('metric-net_revenue')).toHaveText('¥0.00');
  await expect(page.getByTestId('applied-filters')).toContainText('2026-09-01 至 2026-09-30');
  await page.screenshot({path:`${evidence}/concurrency.png`,fullPage:true});
});
