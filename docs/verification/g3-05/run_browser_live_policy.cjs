/* One approved real-browser policy attribute probe; never sends trend chat. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const out = process.env.G305_OUT;
if (!out) throw new Error('G305_OUT required');
const ready = JSON.parse(fs.readFileSync(path.join(out, 'target-ready.json'), 'utf8'));
assert.equal(ready.max_chats, 1);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const record = { baseline: ready.baseline,
    question: '外卖订单退款审核通过后，退款多久能到账？' };
  try {
    await page.goto(ready.base_url);
    await page.getByRole('button', { name: '经营助手', exact: true }).click();
    await page.getByLabel('经营问题').fill(record.question);
    const sent = page.waitForRequest(r => r.url().endsWith('/api/chat'));
    const received = page.waitForResponse(r => r.url().endsWith('/api/chat'));
    await page.getByRole('button', { name: '发送', exact: true }).click();
    record.request = (await sent).postDataJSON();
    const raw = await received;
    record.http_status = raw.status();
    record.response = await raw.json();
    record.trace = await (await page.request.get(`${ready.base_url}/api/trace/${record.response.trace_id}`)).json();
    await page.locator('.chat-answer').last().getByText(record.response.answer).waitFor();
    await page.screenshot({ path: path.join(out, 'policy-browser.png'), animations: 'disabled' });
    fs.writeFileSync(path.join(out, 'policy-browser.json'), JSON.stringify(record, null, 2));
    console.log('G305_POLICY_BROWSER', record.http_status, record.response.answer_type, record.response.answer);
  } catch (error) {
    record.error = String(error);
    fs.writeFileSync(path.join(out, 'policy-browser-failure.json'), JSON.stringify(record, null, 2));
    await page.screenshot({ path: path.join(out, 'policy-browser-failure.png'), animations: 'disabled' });
    throw error;
  } finally {
    fs.writeFileSync(path.join(out, 'target-done'), 'one authorized chat finished\n');
    await page.close();
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
