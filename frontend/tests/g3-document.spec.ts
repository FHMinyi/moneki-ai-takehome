import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const out = path.resolve('../docs/verification/g3-02/browser');
test.beforeAll(() => fs.mkdirSync(out, { recursive: true }));
for (const width of [1280, 1440, 390]) {
  test(`真实文档回答与来源 ${width}`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await page.getByRole('button', { name: '经营助手', exact: true }).click();
    await page.getByLabel('经营问题').fill('外卖订单多久内可以申请退款？');
    const received = page.waitForResponse(r => r.url().endsWith('/api/chat'));
    await page.getByRole('button', { name: '发送', exact: true }).click();
    const answer = await (await received).json();
    expect(answer.answer_type).toBe('doc');
    await expect(page.locator('.chat-answer')).toContainText(answer.answer);
    await page.getByText(`展开文档引用（${answer.citations.length}）`, { exact: true }).click();
    for (const c of answer.citations) {
      await expect(page.locator('.chat-answer blockquote')).toContainText(c.doc_id);
      await expect(page.locator('.chat-answer blockquote')).toContainText(c.quote);
      await expect(page.locator('.chat-answer blockquote')).toContainText(c.metadata.title);
      await expect(page.locator('.chat-answer blockquote')).toContainText(c.metadata.effective_from);
    }
    expect(await page.locator('.chat-history').evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
    const trace = await (await request.get(`/api/trace/${answer.trace_id}`)).json();
    fs.writeFileSync(path.join(out, `http-${width}.json`), JSON.stringify({ answer, trace }, null, 2));
    await page.screenshot({ path: path.join(out, `document-${width}.png`) });
  });
}
test('旧引用与未知元信息兼容', async ({ page }) => {
  await page.route('**/api/chat', r => r.fulfill({ json: { answer: '原文事实。', answer_type: 'doc', citations: [{ doc_id: 'KB-TEST', quote: '原文事实。', metadata: { title: { future: 'unknown' }, effective_from: null }, scope: { as_of: [] }, chunk_id: 42, future: true }], data_evidence: [], trace_id: 'compat-only' } }));
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto('/');
  await page.getByRole('button', { name: '经营助手', exact: true }).click();
  await page.getByLabel('经营问题').fill('兼容性样本');
  await page.getByRole('button', { name: '发送', exact: true }).click();
  await page.getByText('展开文档引用（1）', { exact: true }).click();
  await expect(page.locator('blockquote')).toContainText('KB-TEST');
  await expect(page.locator('blockquote')).not.toContainText('object Object');
  await page.screenshot({ path: path.join(out, 'compat-390.png') });
});
