import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const out=process.env.G303_CROSS_BROWSER_OUT!;
const model=process.env.G303_CROSS_MODEL_URL!;
const first='618 当天 S02 的牛肉poke 卖了多少份？达到目标了吗？';
const why='S03 六月第二周（6 月 8 日到 6 月 14 日）的营业额为什么比别的周低这么多？';
const price='牛肉poke 现在卖多少钱一份？商品表里那个价能直接拿来用吗？';
test.beforeAll(()=>fs.mkdirSync(out,{recursive:true}));
async function configure(request:any,question:string,c:any){await request.post(model+'/case',{data:{question,case:c}});}
async function ask(page:any,request:any,question:string){
 await page.getByLabel('经营问题').fill(question);
 const sent=page.waitForRequest((r:any)=>r.url().endsWith('/api/chat'));const got=page.waitForResponse((r:any)=>r.url().endsWith('/api/chat'));
 await page.getByRole('button',{name:'发送',exact:true}).click();const payload=(await sent).postDataJSON();const answer=await(await got).json();
 await expect(page.locator('.chat-answer').last()).toContainText(answer.answer);
 const trace=await(await request.get('/api/trace/'+answer.trace_id)).json();return {payload,answer,trace};
}
for(const width of [1280,1440,390]) {
 test(`混合后趋势引用与文字覆盖 ${width}`,async({page,request})=>{
  await page.setViewportSize({width,height:900});await page.goto('/');await page.getByRole('button',{name:'经营助手',exact:true}).click();
  const a=await ask(page,request,first);expect(a.answer.answer_type).toBe('hybrid');
  await page.getByRole('button',{name:'Close'}).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await page.getByRole('textbox',{name:'开始日期'}).fill('2026-06-08');await page.getByRole('textbox',{name:'结束日期'}).fill('2026-06-14');
  const stores=(await(await request.get('/api/stores')).json()).stores;const store=stores.find((s:any)=>s.store_id==='S03');
  const visibleSelector=page.locator('.ant-select[aria-label="门店"] .ant-select-selector');
  await visibleSelector.click();
  const option=page.locator('.ant-select-dropdown:visible').getByTitle(store.store_name+' · S03',{exact:true});
  await expect(option).toBeVisible();await option.click();
  await expect(page.locator('.ant-select[aria-label="门店"] .ant-select-selection-item')).toHaveText(store.store_name+' · S03');
  await page.getByRole('button',{name:'查询汇总'}).click();await expect(page.getByTestId('applied-filters')).toContainText('S03');
  await page.getByRole('button',{name:'加入提问',exact:true}).click();
  const q='那这段时间呢？';await configure(request,q,{mode:'anomaly',tool:'query_metrics',params:{start:'2026-06-08',end:'2026-06-14',store_id:'S03'},metric:'net_revenue',doc:'KB-020',needle:'停业 4 天',role:'reason',query:why});
  const b=await ask(page,request,q);expect(b.answer.answer_type).toBe('hybrid');expect(b.payload.session_id).toBe(a.payload.session_id);expect(b.payload.context.store_id).toBe('S03');
  expect(b.answer.data_evidence[0].result.net_revenue).toBe(3630);expect(b.answer.data_evidence[0].params.product_id).toBeUndefined();
  expect(b.trace.steps.find((s:any)=>s.step==='plan').detail.product_id).toBeNull();
  const last=page.locator('.chat-answer').last();await last.getByText(/展开数据证据/).click();await last.getByText(/展开文档引用/).click();
  await expect(last).toContainText(b.answer.citations[0].quote);await expect(last).toContainText(JSON.stringify(b.answer.data_evidence[0].params,null,2));
  await page.screenshot({path:path.join(out,`trend-${width}.png`)});
  const next='7月S01鸡肉poke净营业额是多少？';await configure(request,next,{mode:'data',tool:'query_metrics',params:{start:'2026-07-01',end:'2026-07-31',store_id:'S01',product_id:'P05'},metric:'net_revenue'});
  const c=await ask(page,request,next);expect(c.answer.answer_type).toBe('data');expect(c.payload.context).toBeUndefined();expect(c.answer.data_evidence[0].params.product_id).toBe('P05');
  fs.writeFileSync(path.join(out,`trend-${width}.json`),JSON.stringify({a,b,c},null,2));
 });
 test(`混合价格追问重新取证 ${width}`,async({page,request})=>{
  await page.setViewportSize({width,height:900});await page.goto('/');await page.getByRole('button',{name:'经营助手',exact:true}).click();
  const a=await ask(page,request,price);expect(a.answer.answer_type).toBe('hybrid');
  const q='那7月1日呢？';await configure(request,q,{mode:'price',tool:'unit_price_check',params:{product_id:'P06',start:'2026-07-01',end:'2026-07-01'},metric:'unit_price',doc:'KB-025',needle:'调整为',role:'price',query:'牛肉poke售价调整'});
  const b=await ask(page,request,q);expect(b.answer.answer_type).toBe('hybrid');expect(b.answer.citations[0].scope.as_of).toBe('2026-07-01');expect(b.answer.citations[0].evidence_id).not.toBe(a.answer.citations[0].evidence_id);
  const last=page.locator('.chat-answer').last();await last.getByText(/展开数据证据/).click();await expect(last.getByRole('heading',{name:'计算关系与操作数来源'})).toBeVisible();await last.getByText(/展开文档引用/).click();
  await expect(last).toContainText(b.answer.citations[0].quote);fs.writeFileSync(path.join(out,`price-${width}.json`),JSON.stringify({a,b},null,2));await page.screenshot({path:path.join(out,`price-${width}.png`)});
 });
}
