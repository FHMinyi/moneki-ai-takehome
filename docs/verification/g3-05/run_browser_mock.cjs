/* Real Chromium clicks against the fresh built app and mock backend. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const out = path.join(__dirname, 'browser-mock');
fs.mkdirSync(out, { recursive: true });
const base = 'http://127.0.0.1:8129';

async function ask(page, question) {
  await page.getByLabel('经营问题').fill(question);
  const sent = page.waitForRequest(r => r.url().endsWith('/api/chat'));
  const received = page.waitForResponse(r => r.url().endsWith('/api/chat'));
  await page.getByRole('button', { name: '发送', exact: true }).click();
  const request = (await sent).postDataJSON();
  const response = await (await received).json();
  await page.locator('.chat-answer').last().getByText(response.answer).waitFor();
  return { request, response };
}

async function run(browser, width) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  const record = { width, baseline: '4591fab9a80ef63c440b9a117dbbc4fcbf03c430',
                   mode: 'mock', turns: [] };
  try {
    await page.goto(base);
    await page.getByRole('button', { name: '查询汇总' }).waitFor();
    await page.getByRole('button', { name: '经营助手', exact: true }).click();
    const data = await ask(page, '牛肉poke 六月一共卖了多少钱？');
    assert.equal(data.response.answer_type, 'data');
    await page.locator('.chat-answer').last().getByText(/展开数据证据/).click();
    await page.locator('.chat-answer').last().getByText('query_metrics').waitFor();
    record.turns.push(data);
    const doc = await ask(page, '外卖订单多久内可以申请退款？');
    assert.equal(doc.response.answer_type, 'doc');
    assert.equal(doc.response.citations[0].doc_id, 'KB-013');
    await page.locator('.chat-answer').last().getByText(/展开文档引用/).click();
    await page.locator('.chat-answer').last().getByText(/24 小时/).first().waitFor();
    record.turns.push(doc);
    const hybrid = await ask(page, '618 当天 S02 的牛肉poke 卖了多少份？达到目标了吗？');
    assert.equal(hybrid.response.answer_type, 'hybrid');
    await page.locator('.chat-answer').last().getByText(/展开数据证据/).click();
    await page.locator('.chat-answer').last().getByText(/展开文档引用/).click();
    record.turns.push(hybrid);
    await page.screenshot({ path: path.join(out, `answers-${width}.png`), animations: 'disabled' });
    await page.getByRole('button', { name: '新建对话' }).click();
    assert.equal(await page.locator('.chat-turn').count(), 0);
    record.turns.push(await ask(page, '6 月的净营业额是多少？'));
    const followup = await ask(page, '那 7 月呢？');
    assert.equal(followup.response.answer_type, 'data');
    record.turns.push(followup);
    await page.getByRole('button', { name: 'Close' }).click();
    await page.getByRole('textbox', { name: '开始日期' }).fill('2026-07-01');
    await page.getByRole('textbox', { name: '结束日期' }).fill('2026-07-31');
    // Click the visible AntD selector, not its transparent combobox input.
    await page.locator('.ant-select-selector').first().click();
    const stores = (await (await page.request.get(base + '/api/stores')).json()).stores;
    const s01 = stores.find(s => s.store_id === 'S01');
    await page.getByTitle(`${s01.store_name} · S01`, { exact: true }).click();
    await page.getByRole('button', { name: '查询汇总' }).click();
    await page.getByRole('button', { name: '加入提问' }).click();
    const card = page.getByTestId('trend-reference');
    await card.getByText('2026-07-01 至 2026-07-31').waitFor();
    const trend = await ask(page, '这段时间净营业额是多少？');
    assert.deepEqual(trend.request.context, { type: 'daily_trend', start: '2026-07-01',
      end: '2026-07-31', store_id: 'S01', metric: 'net_revenue' });
    assert.equal(trend.response.answer_type, 'data');
    record.turns.push(trend);
    await page.screenshot({ path: path.join(out, `trend-${width}.png`), animations: 'disabled' });
    await page.getByRole('button', { name: '新建对话' }).click();
    assert.equal(await page.getByTestId('trend-reference').count(), 0);
    let first = true;
    const attempts = [];
    await page.route('**/api/chat', async route => {
      attempts.push(route.request().postDataJSON());
      if (first) { first = false; await route.fulfill({ status: 503, json: { error: 'controlled failure' } }); }
      else await route.continue();
    });
    await page.getByLabel('经营问题').fill('S02 六月净营业额是多少？');
    await page.getByRole('button', { name: '发送', exact: true }).click();
    await page.getByRole('button', { name: '重试这条问题' }).click();
    await page.locator('.chat-answer').last().getByText(/净营业额/).waitFor();
    assert.deepEqual(attempts[1], attempts[0]);
    record.retry = attempts;
    fs.writeFileSync(path.join(out, `browser-${width}.json`), JSON.stringify(record, null, 2));
    console.log(width, 'PASS', record.turns.map(x => x.response.answer_type).join(','));
  } catch (error) {
    record.error = String(error);
    fs.writeFileSync(path.join(out, `browser-${width}-failure.json`), JSON.stringify(record, null, 2));
    await page.screenshot({ path: path.join(out, `failure-${width}.png`), animations: 'disabled' });
    throw error;
  } finally {
    await page.close();
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try { for (const width of [1280, 1440, 390]) await run(browser, width); }
  finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
