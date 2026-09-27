import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const out=process.env.G303_DOC_DATE_BROWSER!;const model=process.env.G303_DOC_DATE_MODEL!;
test.beforeAll(()=>fs.mkdirSync(out,{recursive:true}));
for(const width of [1280,390])test(`mixed minimal doc and exact day ${width}`,async({page,request})=>{
 await page.setViewportSize({width,height:900});await page.goto('/');await page.getByRole('button',{name:'经营助手',exact:true}).click();
 const cases:any[]=[
  {q:'牛肉poke 现在卖多少钱一份？商品表里那个价能直接拿来用吗？',type:'hybrid',c:null},
  {q:'外卖订单多久内可以退款？',type:'doc',c:{mode:'doc',doc:'KB-013',needle:'24',query:'外卖订单多久内可以退款？'}},
  {q:'S02 6月18日牛肉poke销量是多少？',type:'data',c:{mode:'data',tool:'query_metrics',params:{start:'2026-06-18',end:'2026-06-18',store_id:'S02',product_id:'P06'},metric:'qty'}},
 ];
 const turns=[];
 for(const item of cases){
  if(item.c)await request.post(model+'/case',{data:{question:item.q,case:item.c}});
  await page.getByLabel('经营问题').fill(item.q);const pending=page.waitForResponse(r=>r.url().endsWith('/api/chat'));
  await page.getByRole('button',{name:'发送',exact:true}).click();const a=await(await pending).json();expect(a.answer_type).toBe(item.type);
  const trace=await(await request.get('/api/trace/'+a.trace_id)).json();expect(trace.errors).toEqual([]);
  expect(trace.llm_calls.every((call:any)=>call.request.max_tokens===8192)).toBe(true);
  const last=page.locator('.chat-answer').last();await expect(last).toContainText(a.answer);
  if(a.citations.length){await last.getByText(/展开文档引用/).click();for(const [i,c] of a.citations.entries())await expect(last.locator('blockquote').nth(i)).toContainText(c.quote);}
  if(item.type==='doc'){const final=JSON.parse(trace.llm_calls.at(-1).response.choices[0].message.content);expect(Object.keys(final.facts[0])).toEqual(['evidence_id']);}
  if(item.type==='data'){
   expect(a.data_evidence[0].params).toEqual(item.c.params);expect(a.data_evidence[0].result.qty).toBe(125);
   await last.getByText(/展开数据证据/).click();await expect(last).toContainText('2026-06-18');
   expect(trace.steps.some((s:any)=>s.step==='explicit_data_scope')).toBe(true);
  }
  turns.push({question:item.q,answer:a,trace});
 }
 fs.writeFileSync(path.join(out,`sequence-${width}.json`),JSON.stringify({mode:'CONTROLLED_NEW_SELECTIONS_NO_PROVIDER',turns},null,2));
 await page.screenshot({path:path.join(out,`sequence-${width}.png`)});
});

for(const width of [1280,390])test(`mixed to exact day natural followup ${width}`,async({page,request})=>{
 await page.setViewportSize({width,height:900});await page.goto('/');await page.getByRole('button',{name:'经营助手',exact:true}).click();
 const first='618 当天 S02 的牛肉poke 卖了多少份？达到目标了吗？';const next='那6月19日销量呢？';
 const rows=[
  {q:first,type:'hybrid',c:{mode:'target',tool:'query_metrics',params:{start:'2026-06-18',end:'2026-06-18',store_id:'S02',product_id:'P06'},metric:'qty',doc:'KB-023',needle:'当天牛肉poke 目标销量',role:'target'}},
  {q:next,type:'data',c:{mode:'data',tool:'query_metrics',params:{start:'2026-06-19',end:'2026-06-19',store_id:'S02',product_id:'P06'},metric:'qty'}},
 ];const turns=[];
 for(const item of rows){
  await request.post(model+'/case',{data:{question:item.q,case:item.c}});await page.getByLabel('经营问题').fill(item.q);
  const pending=page.waitForResponse(r=>r.url().endsWith('/api/chat'));await page.getByRole('button',{name:'发送',exact:true}).click();
  const answer=await(await pending).json();expect(answer.answer_type).toBe(item.type);
  const trace=await(await request.get('/api/trace/'+answer.trace_id)).json();expect(trace.errors).toEqual([]);
  await expect(page.locator('.chat-answer').last()).toContainText(answer.answer);turns.push({question:item.q,answer,trace});
 }
 const last=turns.at(-1)!;expect(last.answer.data_evidence[0].params).toEqual(rows[1].c.params);
 const scope=last.trace.steps.find((s:any)=>s.step==='explicit_data_scope').detail;
 expect(scope.bound_entities).toEqual([]);expect('store_id' in scope).toBe(false);expect('product_id' in scope).toBe(false);
 await page.locator('.chat-answer').last().getByText(/展开数据证据/).click();
 fs.writeFileSync(path.join(out,`natural-${width}.json`),JSON.stringify({mode:'CONTROLLED_NEW_SELECTIONS_NO_PROVIDER',turns},null,2));
 await page.screenshot({path:path.join(out,`natural-${width}.png`)});
});
