/* Exactly two user-visible /api/chat requests on the guarded target service. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const out = process.env.G305_OUT;
if (!out) throw new Error('G305_OUT is required');
const ready = JSON.parse(fs.readFileSync(path.join(out, 'target-ready.json'), 'utf8'));
assert.equal(ready.max_chats, 2);
const base = ready.base_url;

async function ask(page, question) {
  await page.getByLabel('经营问题').fill(question);
  const requestPromise = page.waitForRequest(r => r.url().endsWith('/api/chat'));
  const responsePromise = page.waitForResponse(r => r.url().endsWith('/api/chat'));
  await page.getByRole('button', { name: '发送', exact: true }).click();
  const request = (await requestPromise).postDataJSON();
  const raw = await responsePromise;
  const response = await raw.json();
  const trace = await (await page.request.get(`${base}/api/trace/${response.trace_id}`)).json();
  await page.locator('.chat-answer').last().getByText(response.answer).waitFor();
  return { question, request, http_status: raw.status(), response, trace };
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const record = { baseline: ready.baseline, base_url: base, turns: [],
                   purpose: 'two pre-approved real model targeted chats' };
  try {
    await page.goto(base);
    await page.getByRole('button', { name: '查询汇总' }).waitFor();
    await page.getByRole('textbox', { name: '开始日期' }).fill('2026-06-08');
    await page.getByRole('textbox', { name: '结束日期' }).fill('2026-06-14');
    await page.locator('.ant-select-selector').first().click();
    const stores = (await (await page.request.get(`${base}/api/stores`)).json()).stores;
    const s03 = stores.find(s => s.store_id === 'S03');
    await page.getByTitle(`${s03.store_name} · S03`, { exact: true }).click();
    await page.getByRole('button', { name: '查询汇总' }).click();
    await page.getByRole('button', { name: '加入提问' }).click();
    const card = page.getByTestId('trend-reference');
    await card.getByText('2026-06-08 至 2026-06-14').waitFor();
    await card.getByText(/S03/).waitFor();
    const first = await ask(page, '这段时间的净营业额为什么比前一周低？');
    assert.deepEqual(first.request.context, { type: 'daily_trend', start: '2026-06-08',
      end: '2026-06-14', store_id: 'S03', metric: 'net_revenue' });
    record.turns.push(first);
    fs.writeFileSync(path.join(out, 'target-browser-first.json'), JSON.stringify(first, null, 2));
    await page.screenshot({ path: path.join(out, 'target-browser-trend.png'), animations: 'disabled' });
    await page.getByRole('button', { name: '新建对话' }).click();
    const second = await ask(page, '外卖订单退款审核通过后，退款多久能到账？');
    assert.notEqual(second.request.session_id, first.request.session_id);
    assert.equal(Object.hasOwn(second.request, 'context'), false);
    record.turns.push(second);
    fs.writeFileSync(path.join(out, 'target-browser-second.json'), JSON.stringify(second, null, 2));
    await page.screenshot({ path: path.join(out, 'target-browser-doc-negative.png'), animations: 'disabled' });
    fs.writeFileSync(path.join(out, 'target-browser.json'), JSON.stringify(record, null, 2));
    console.log('G305_TARGET_BROWSER', record.turns.map(x => [x.http_status, x.response.answer_type]));
  } catch (error) {
    record.error = String(error);
    fs.writeFileSync(path.join(out, 'target-browser-failure.json'), JSON.stringify(record, null, 2));
    await page.screenshot({ path: path.join(out, 'target-browser-failure.png'), animations: 'disabled' });
    throw error;
  } finally {
    fs.writeFileSync(path.join(out, 'target-done'), 'browser client finished\n');
    await page.close();
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
