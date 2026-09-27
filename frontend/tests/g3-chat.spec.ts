import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const out = path.resolve('../docs/verification/g3-01/browser');
test.describe.configure({ mode: 'serial' });
test.beforeAll(() => fs.mkdirSync(out, { recursive: true }));
test.beforeEach(async ({ request }) => {
  await request.post('http://127.0.0.1:9032/case', { data: {} });
});

for (const width of [1280, 1440, 390]) {
  test(`真实查数、证据和长输入 ${width}`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.getByTestId('applied-filters')).toBeVisible();
    const filters = await page.getByTestId('applied-filters').innerText();
    await page.getByRole('button', { name: '经营助手', exact: true }).click();
    await page.getByLabel('经营问题').fill('S02 六月牛肉poke卖了多少份？');
    const sent = page.waitForRequest(r => r.url().endsWith('/api/chat'));
    const received = page.waitForResponse(r => r.url().endsWith('/api/chat'));
    await page.getByRole('button', { name: '发送', exact: true }).click();
    const payload = (await sent).postDataJSON();
    expect(Object.keys(payload).sort()).toEqual(['question', 'session_id']);
    const answer = await (await received).json();
    expect(answer.answer_type).toBe('data');
    await expect(page.locator('.chat-answer')).toContainText(answer.answer);
    await page.getByText('展开数据证据（1）', { exact: true }).click();
    await expect(page.locator('.chat-evidence')).toContainText(String(answer.data_evidence[0].result.qty));
    await expect(page.locator('.chat-evidence')).toContainText('2026-06-01');
    await expect(page.locator('.chat-answer')).not.toContainText('CONTROLLED_PRIVATE_REASONING');
    const trace = await (await request.get(`/api/trace/${answer.trace_id}`)).json();
    fs.writeFileSync(path.join(out, `http-${width}.json`), JSON.stringify({ payload, answer, trace }, null, 2));
    await page.getByLabel('经营问题').fill('请核对这段完整经营问题。'.repeat(100));
    const textarea = await page.getByLabel('经营问题').boundingBox();
    const send = await page.getByRole('button', { name: '发送', exact: true }).boundingBox();
    expect(textarea!.x).toBeGreaterThanOrEqual(0);
    expect(textarea!.x + textarea!.width).toBeLessThanOrEqual(width);
    expect(send!.y + send!.height).toBeLessThanOrEqual(900);
    await page.screenshot({ path: path.join(out, `chat-${width}.png`), fullPage: false });
    await page.getByRole('button', { name: 'Close' }).click();
    await expect(page.getByTestId('applied-filters')).toHaveText(filters);
  });
}

test('等待防重复、新会话丢弃旧响应、失败重试', async ({ page, request }) => {
  await page.goto('/');
  await page.getByRole('button', { name: '经营助手', exact: true }).click();
  await request.post('http://127.0.0.1:9032/case', { data: { delay: 2 } });
  const sent: any[] = [];
  page.on('request', r => { if (r.url().endsWith('/api/chat')) sent.push(r.postDataJSON()); });
  await page.getByLabel('经营问题').fill('S02 六月牛肉poke销量，旧问题。');
  await page.getByRole('button', { name: '发送', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('正在查询');
  await expect(page.getByRole('button', { name: '发送', exact: true })).toBeDisabled();
  await page.getByLabel('经营问题').press('Control+Enter');
  expect(sent.length).toBe(1);
  await page.getByRole('button', { name: '新建对话' }).click();
  await request.post('http://127.0.0.1:9032/case', { data: { status: 503 } });
  await page.getByLabel('经营问题').fill('S02 六月牛肉poke销量，新问题。');
  await page.getByRole('button', { name: '发送', exact: true }).click();
  await expect(page.getByRole('button', { name: '重试这条问题' })).toBeVisible();
  expect(sent[0].session_id).not.toBe(sent[1].session_id);
  await request.post('http://127.0.0.1:9032/case', { data: {} });
  await page.getByRole('button', { name: '重试这条问题' }).click();
  await expect(page.locator('.chat-answer')).toContainText('销量 417 件');
  await page.waitForTimeout(2200);
  await expect(page.getByLabel('聊天记录')).not.toContainText('旧问题');
  expect(sent.length).toBe(3);
  expect(sent[2].session_id).toBe(sent[1].session_id);
  fs.writeFileSync(path.join(out, 'lifecycle-requests.json'), JSON.stringify(sent, null, 2));
  await page.screenshot({ path: path.join(out, 'lifecycle.png'), fullPage: false });
});
