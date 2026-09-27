import { test, expect, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const out = path.resolve(process.env.G306_EVIDENCE_DIR || '../docs/verification/g3-06/browser');
test.beforeAll(() => fs.mkdirSync(out, { recursive: true }));
async function setControlledModel(request: import('@playwright/test').APIRequestContext, params: Record<string, unknown>) {
  if (process.env.G306_MODEL_URL) {
    await request.post(`${process.env.G306_MODEL_URL}/case`, { data: { tool: 'query_metrics', params, metric: 'net_revenue' } });
  }
}

async function apply(page: Page, start: string, end: string, store: string) {
  await page.getByRole('textbox', { name: '开始日期' }).fill(start);
  await page.getByRole('textbox', { name: '结束日期' }).fill(end);
  await page.getByRole('combobox', { name: '门店' }).press('ArrowDown');
  await page.getByTitle(store, { exact: true }).click();
  await page.getByRole('button', { name: '查询汇总' }).click();
  await expect(page.getByRole('button', { name: '加入提问' })).toBeVisible();
}

for (const width of [1280, 1440, 390]) {
  test(`每日趋势引用生命周期 ${width}`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    const stores = (await (await request.get('/api/stores')).json()).stores;
    const s02 = `${stores.find((s: {store_id: string}) => s.store_id === 'S02').store_name} · S02`;
    const s01 = `${stores.find((s: {store_id: string}) => s.store_id === 'S01').store_name} · S01`;
    await apply(page, '2026-06-01', '2026-06-30', s02);
    await page.getByRole('button', { name: /2026-06-15 净营业额/ }).click();
    await page.getByRole('button', { name: '加入提问' }).click();
    const pending = page.locator('.chat-composer').getByTestId('trend-reference');
    await expect(pending).toContainText('2026-06-01 至 2026-06-30');
    await expect(pending).toContainText('S02');
    await expect(pending).not.toContainText('2026-06-15');
    await page.getByRole('button', { name: 'Close' }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await page.getByRole('textbox', { name: '开始日期' }).fill('2026-07-01');
    await page.getByRole('textbox', { name: '结束日期' }).fill('2026-07-31');
    await page.getByRole('button', { name: '经营助手', exact: true }).click();
    await expect(pending).toContainText('2026-06-01 至 2026-06-30');
    await pending.getByRole('button', { name: '移除趋势引用' }).click();
    await expect(pending).toHaveCount(0);
    await page.getByRole('button', { name: 'Close' }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await page.getByRole('combobox', { name: '门店' }).press('ArrowDown');
    await page.getByTitle(s01, { exact: true }).click();
    await page.getByRole('button', { name: '查询汇总' }).click();
    await expect(page.getByTestId('applied-filters')).toContainText('S01');
    await page.getByRole('button', { name: '加入提问' }).click();
    await expect(pending).toContainText('2026-07-01 至 2026-07-31');
    await expect(pending).toContainText('S01');
    const before = await request.get('/api/metrics/summary?start=2026-07-01&end=2026-07-31&store_id=S01');
    const expected = await before.json();
    await setControlledModel(request, { start: '2026-07-01', end: '2026-07-31', store_id: 'S01', product_id: null });
    await page.getByLabel('经营问题').fill('这段时间净营业额是多少？');
    const sent = page.waitForRequest(r => r.url().endsWith('/api/chat'));
    const received = page.waitForResponse(r => r.url().endsWith('/api/chat'));
    await page.getByRole('button', { name: '发送', exact: true }).click();
    const payload = (await sent).postDataJSON();
    const answer = await (await received).json();
    expect(payload.context).toEqual({ type: 'daily_trend', start: '2026-07-01', end: '2026-07-31', store_id: 'S01', metric: 'net_revenue' });
    expect(answer.answer_type).toBe('data');
    expect(answer.data_evidence[0].result).toEqual(expected);
    await expect(page.locator('.chat-question')).toContainText('2026-07-01 至 2026-07-31');
    await expect(pending).toHaveCount(0);
    const trace = await (await request.get(`/api/trace/${answer.trace_id}`)).json();
    expect(trace.steps.find((s: {step: string}) => s.step === 'request').detail.context).toEqual(payload.context);
    expect(trace.steps.find((s: {step: string}) => s.step === 'context_resolution').detail.effective.start).toBe('2026-07-01');
    fs.writeFileSync(path.join(out, `lifecycle-${width}.json`), JSON.stringify({ payload, answer, trace, expected }, null, 2));
    await page.screenshot({ path: path.join(out, `lifecycle-${width}.png`), animations: 'disabled' });
    await page.getByRole('button', { name: 'Close' }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await apply(page, '2026-06-01', '2026-06-30', s02);
    await page.getByRole('button', { name: '经营助手', exact: true }).click();
    await expect(page.locator('.chat-question')).toContainText('2026-07-01 至 2026-07-31');
    await page.getByRole('button', { name: '新建对话' }).click();
    await expect(page.getByTestId('trend-reference')).toHaveCount(0);
    await expect(page.getByLabel('聊天记录')).not.toContainText('2026-07-01 至 2026-07-31');
  });
}

test('引用提问失败重试保留原问题和范围', async ({ page, request }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: '加入提问' })).toBeVisible();
  await page.getByRole('button', { name: '加入提问' }).click();
  const sent: any[] = [];
  let fail = true;
  await page.route('**/api/chat', async route => {
    sent.push(route.request().postDataJSON());
    if (fail) { fail = false; await route.fulfill({ status: 503, json: { error: 'controlled failure' } }); }
    else await route.continue();
  });
  await setControlledModel(request, { start: '2026-05-01', end: '2026-08-31', store_id: null, product_id: null });
  await page.getByLabel('经营问题').fill('这段时间净营业额是多少？');
  await page.getByRole('button', { name: '发送', exact: true }).click();
  await expect(page.getByRole('button', { name: '重试这条问题' })).toBeVisible();
  await page.getByRole('button', { name: '重试这条问题' }).click();
  await expect(page.locator('.chat-answer')).toContainText('净营业额');
  expect(sent[1]).toEqual(sent[0]);
  await page.getByRole('button', { name: '新建对话' }).click();
  await expect(page.getByTestId('trend-reference')).toHaveCount(0);
  fs.writeFileSync(path.join(out, 'retry-requests.json'), JSON.stringify(sent, null, 2));
});

test('新对话丢弃旧引用请求的迟到响应', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: '加入提问' })).toBeVisible();
  await page.getByRole('button', { name: '加入提问' }).click();
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const seen: any[] = [];
  await page.route('**/api/chat', async route => {
    seen.push(route.request().postDataJSON());
    await gate;
    await route.fulfill({ json: { answer: '过时结果', answer_type: 'data', citations: [], data_evidence: [], trace_id: 'old' } }).catch(() => {});
  });
  await page.getByLabel('经营问题').fill('这段时间净营业额是多少？');
  await page.getByRole('button', { name: '发送', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('正在查询');
  await page.getByRole('button', { name: '新建对话' }).click();
  release();
  await expect(page.getByLabel('聊天记录')).not.toContainText('过时结果');
  await expect(page.getByTestId('trend-reference')).toHaveCount(0);
  expect(seen[0].context.type).toBe('daily_trend');
});

test('加载与错误状态不提供引用，重复加入替换待发卡片', async ({ page, request }) => {
  let blocked = true;
  await page.route('**/api/metrics/daily?**', async route => {
    if (blocked) { blocked = false; await route.fulfill({ status: 503, json: { error: 'controlled daily failure' } }); }
    else await route.continue();
  });
  await page.goto('/');
  await expect(page.getByText('每日趋势加载失败')).toBeVisible();
  await expect(page.getByRole('button', { name: '加入提问' })).toHaveCount(0);
  await page.getByRole('button', { name: '重试趋势' }).click();
  await expect(page.getByRole('button', { name: '加入提问' })).toBeVisible();
  await page.getByRole('button', { name: '加入提问' }).click();
  const pending = page.locator('.chat-composer').getByTestId('trend-reference');
  await expect(pending).toContainText('2026-05-01 至 2026-08-31');
  await page.getByRole('button', { name: 'Close' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  const stores = (await (await request.get('/api/stores')).json()).stores;
  const s02 = `${stores.find((s: {store_id: string}) => s.store_id === 'S02').store_name} · S02`;
  await apply(page, '2026-06-01', '2026-06-30', s02);
  await page.getByRole('button', { name: '加入提问' }).click();
  await expect(pending).toHaveCount(1);
  await expect(pending).toContainText('2026-06-01 至 2026-06-30');
  await expect(pending).not.toContainText('2026-05-01 至 2026-08-31');
});

test('普通无引用提问仍使用旧请求形状', async ({ page, request }) => {
  await page.goto('/');
  await page.getByRole('button', { name: '经营助手', exact: true }).click();
  await setControlledModel(request, { start: '2026-06-01', end: '2026-06-30', store_id: 'S02', product_id: null });
  await page.getByLabel('经营问题').fill('S02 六月净营业额是多少？');
  const sent = page.waitForRequest(r => r.url().endsWith('/api/chat'));
  const received = page.waitForResponse(r => r.url().endsWith('/api/chat'));
  await page.getByRole('button', { name: '发送', exact: true }).click();
  const payload = (await sent).postDataJSON();
  const answer = await (await received).json();
  expect(Object.keys(payload).sort()).toEqual(['question', 'session_id']);
  expect(answer.answer_type).toBe('data');
  expect(answer.data_evidence[0].result).toEqual(await (await request.get('/api/metrics/summary?start=2026-06-01&end=2026-06-30&store_id=S02')).json());
  await expect(page.getByTestId('trend-reference')).toHaveCount(0);
});
