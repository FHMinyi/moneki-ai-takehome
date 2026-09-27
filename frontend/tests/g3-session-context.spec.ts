import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const out = path.resolve('../docs/verification/g3-04/browser');
test.describe.configure({ mode: 'serial' });
test.beforeAll(() => fs.mkdirSync(out, { recursive: true }));

for (const width of [1280, 1440, 390]) {
  test(`多轮取数和新建对话 ${width}`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await page.getByRole('button', { name: '经营助手', exact: true }).click();
    const turns = [];
    for (const [index, question] of ['6 月的净营业额是多少？', '那 7 月呢？', '这两个月的客单价差了多少？'].entries()) {
      if (index === 1) {
        await page.getByRole('button', { name: 'Close' }).click();
        await page.getByRole('textbox', { name: '开始日期' }).fill('2026-08-01');
        await page.getByRole('textbox', { name: '结束日期' }).fill('2026-08-31');
        await page.getByRole('button', { name: '查询汇总' }).click();
        await expect(page.getByTestId('applied-filters')).toContainText('2026-08-01');
        await page.getByRole('button', { name: '经营助手', exact: true }).click();
      }
      await page.getByLabel('经营问题').fill(question);
      const sent = page.waitForRequest(r => r.url().endsWith('/api/chat'));
      const received = page.waitForResponse(r => r.url().endsWith('/api/chat'));
      await page.getByRole('button', { name: '发送', exact: true }).click();
      const payload = (await sent).postDataJSON();
      expect(Object.keys(payload).sort()).toEqual(['question', 'session_id']);
      const answer = await (await received).json();
      const trace = await (await request.get(`/api/trace/${answer.trace_id}`)).json();
      turns.push({ payload, answer, trace });
      await expect(page.locator('.chat-answer')).toHaveCount(turns.length);
      await expect(page.locator('.chat-answer').last()).toContainText(answer.answer);
    }
    expect(turns.map(t => t.payload.session_id).filter((id, i, a) => id === a[0])).toHaveLength(3);
    expect(turns.map(t => t.answer.answer_type)).toEqual(['data', 'data', 'data']);
    expect(turns[0].answer.answer).toContain('156757.00');
    expect(turns[1].answer.answer).toContain('162414.00');
    expect(turns[2].answer.answer).toContain('0.17');
    expect(turns[2].trace.steps.find((s: {step: string}) => s.step === 'session_context').detail.history_size).toBe(2);
    fs.writeFileSync(path.join(out, `multiturn-${width}.json`), JSON.stringify(turns, null, 2));
    await page.screenshot({ path: path.join(out, `multiturn-${width}.png`), animations: 'disabled' });
    await page.getByRole('button', { name: '新建对话' }).click();
    await expect(page.locator('.chat-turn')).toHaveCount(0);
    await page.getByLabel('经营问题').fill('那 7 月呢？');
    const sent = page.waitForRequest(r => r.url().endsWith('/api/chat'));
    await page.getByRole('button', { name: '发送', exact: true }).click();
    const newSession = (await sent).postDataJSON().session_id;
    expect(newSession).not.toBe(turns[0].payload.session_id);
    await expect(page.locator('.chat-answer')).toContainText('没有上文');
  });
}

test('旧请求迟到后不进入新会话', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: '经营助手', exact: true }).click();
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/chat', async route => {
    await gate;
    await route.fulfill({ json: { answer: '过时回答', answer_type: 'data', citations: [], data_evidence: [], trace_id: 'old' } }).catch(() => {});
  });
  await page.getByLabel('经营问题').fill('6 月的净营业额是多少？');
  await page.getByRole('button', { name: '发送', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('正在查询');
  await page.getByRole('button', { name: '新建对话' }).click();
  release();
  await expect(page.locator('.chat-turn')).toHaveCount(0);
  await expect(page.getByLabel('聊天记录')).not.toContainText('过时回答');
});
