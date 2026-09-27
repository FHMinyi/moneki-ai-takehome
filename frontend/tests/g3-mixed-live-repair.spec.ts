import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const out=process.env.G303_REPAIR_BROWSER!;
test.beforeAll(()=>fs.mkdirSync(out,{recursive:true}));
const cases=[
 ['C07',['S04 为什么不卖吞拿鱼三明治了？']],
 ['T02-1',['三文鱼poke 七月初为什么停售了？']],
 ['H04',['牛肉poke 现在卖多少钱一份？商品表里那个价能直接拿来用吗？']],
 ['T03-2',['牛肉poke 现在多少钱一份？','那 6 月 18 号那天呢？']],
] as const;
for(const width of [1280,1440,390]) for(const [name,questions] of cases){
 test(`saved mixed repair ${name} ${width}`,async({page,request})=>{
  await page.setViewportSize({width,height:900});await page.goto('/');
  await page.getByRole('button',{name:'经营助手',exact:true}).click();
  const records=[];
  for(const q of questions){
   await page.getByLabel('经营问题').fill(q);
   const got=page.waitForResponse(r=>r.url().endsWith('/api/chat'));
   await page.getByRole('button',{name:'发送',exact:true}).click();
   const answer=await(await got).json();expect(answer.answer_type).toBe('hybrid');
   const trace=await(await request.get('/api/trace/'+answer.trace_id)).json();expect(trace.errors).toEqual([]);
   await expect(page.locator('.chat-answer').last()).toContainText(answer.answer);records.push({q,answer,trace});
  }
  const {answer}=records.at(-1)!;const last=page.locator('.chat-answer').last();
  await last.getByText(/展开数据证据/).click();await last.getByText(/展开文档引用/).click();
  for(const [i,c] of answer.citations.entries())await expect(last.locator('blockquote').nth(i)).toContainText(c.quote);
  for(const e of answer.data_evidence)await expect(last.locator('.chat-evidence')).toContainText(JSON.stringify(e.result,null,2));
  if(name==='C07'){expect(answer.answer).toContain('35%');expect(answer.answer).toContain('补充数据对照');expect(answer.answer).toContain('吞拿鱼三明治的去留');}
  if(name==='T02-1')expect(answer.answer).toContain('质检不合格');
  if(name==='H04')expect(answer.citations.map((c:any)=>c.doc_id)).toEqual(expect.arrayContaining(['KB-025','KB-001']));
  if(name==='T03-2'){expect(answer.answer).toContain('适用门店：S02');expect(answer.answer).toContain('S03 实收单价 42.00');expect(answer.answer).toContain('S05 实收单价 42.00');}
  expect(await page.locator('.chat-history').evaluate(e=>e.scrollWidth<=e.clientWidth+1)).toBe(true);
  fs.writeFileSync(path.join(out,`${name}-${width}.json`),JSON.stringify({mode:'FREE_REPLAY_NOT_PROVIDER_RETRY',records},null,2));
  await page.screenshot({path:path.join(out,`${name}-${width}.png`)});
 });
}
