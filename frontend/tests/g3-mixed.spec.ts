import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const out = process.env.G303_BROWSER_OUT!;
const cases = [
 ['anomaly', 'S03 六月第二周（6 月 8 日到 6 月 14 日）的营业额为什么比别的周低这么多？', 'hybrid'],
 ['target', '618 当天 S02 的牛肉poke 卖了多少份？达到目标了吗？', 'hybrid'],
 ['month-target', '冷萃乌龙茶上市第一个月的销量达标了吗？', 'hybrid'],
 ['price', '牛肉poke 现在卖多少钱一份？商品表里那个价能直接拿来用吗？', 'hybrid'],
 ['zero', 'S02 在 8 月 17 日到 19 日为什么一分钱营业额都没有？', 'data'],
 ['payment', '8 月 3 日 S05 的现金支付占比是多少？为什么会这样？', 'hybrid'],
];
test.beforeAll(()=>fs.mkdirSync(out,{recursive:true}));
for (const width of [1280,1440,390]) for (const [name,question,type] of cases) {
 test(`${name} mixed evidence ${width}`, async ({page,request})=>{
  await page.setViewportSize({width,height:900});await page.goto('/');
  await page.getByRole('button',{name:'经营助手',exact:true}).click();
  await page.getByLabel('经营问题').fill(question);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/chat'));
  await page.getByRole('button',{name:'发送',exact:true}).click();
  const a=await (await response).json();expect(a.answer_type).toBe(type);
  await expect(page.locator('.chat-answer > p')).toHaveText(a.answer);
  await page.getByText(`展开数据证据（${a.data_evidence.length}）`,{exact:true}).click();
  const e=a.data_evidence[0];await expect(page.locator('.chat-evidence')).toContainText(JSON.stringify(e.params,null,2));
  await expect(page.locator('.chat-evidence')).toContainText(JSON.stringify(e.result,null,2));
  if(e.calculations.length){await expect(page.getByRole('heading',{name:'计算关系与操作数来源'})).toBeVisible();await expect(page.locator('.chat-evidence')).toContainText(JSON.stringify(e.calculations,null,2));}
  if(a.citations.length){await page.getByText(`展开文档引用（${a.citations.length}）`,{exact:true}).click();for(const [i,c] of a.citations.entries())await expect(page.locator('blockquote').nth(i)).toContainText(c.quote);}
  else {await expect(page.getByText(/展开文档引用/)).toHaveCount(0);expect(a.answer).toContain('未找到');}
  const trace=await(await request.get('/api/trace/'+a.trace_id)).json();expect(trace.errors).toEqual([]);
  expect(await page.locator('.chat-history').evaluate(el=>el.scrollWidth<=el.clientWidth+1)).toBe(true);
  fs.writeFileSync(path.join(out,`${name}-${width}.json`),JSON.stringify({question,response:a,trace},null,2));
  await page.screenshot({path:path.join(out,`${name}-${width}.png`)});
 });
}
