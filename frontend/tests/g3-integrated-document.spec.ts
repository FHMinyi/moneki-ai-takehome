import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const out=path.resolve(process.env.G302_INTEGRATION_OUT || '../docs/verification/g3-02/integration-g306/browser-doc');
const model=process.env.G306_MODEL_URL!;
test.beforeAll(()=>fs.mkdirSync(out,{recursive:true}));
for(const width of [1280,1440,390]) {
 test(`趋势卡与真实文档引用共存 ${width}`,async({page,request})=>{
  await request.post(model+'/case',{data:{mode:'doc'}});
  await page.setViewportSize({width,height:900});await page.goto('/');
  await expect(page.getByRole('button',{name:'加入提问',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'加入提问',exact:true}).click();
  await expect(page.locator('.chat-composer').getByTestId('trend-reference')).toBeVisible();
  await page.getByLabel('经营问题').fill('外卖订单多久内可以申请退款？');
  const sent=page.waitForRequest(r=>r.url().endsWith('/api/chat'));
  const received=page.waitForResponse(r=>r.url().endsWith('/api/chat'));
  await page.getByRole('button',{name:'发送',exact:true}).click();
  const payload=(await sent).postDataJSON();const answer=await(await received).json();
  expect(payload.context.type).toBe('daily_trend');expect(answer.answer_type).toBe('doc');
  await expect(page.locator('.chat-question').getByTestId('trend-reference')).toBeVisible();
  await expect(page.locator('.chat-composer').getByTestId('trend-reference')).toHaveCount(0);
  await page.getByText(`展开文档引用（${answer.citations.length}）`,{exact:true}).click();
  for(const [i,c] of answer.citations.entries()) await expect(page.locator('.chat-answer blockquote').nth(i)).toContainText(c.quote);
  expect(await page.locator('.chat-history').evaluate(el=>el.scrollWidth<=el.clientWidth+1)).toBe(true);
  const trace=await(await request.get('/api/trace/'+answer.trace_id)).json();expect(trace.errors).toEqual([]);
  fs.writeFileSync(path.join(out,`document-context-${width}.json`),JSON.stringify({payload,answer,trace},null,2));
  await page.screenshot({path:path.join(out,`document-context-${width}.png`)});
 });
}
