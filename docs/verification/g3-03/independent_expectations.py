"""Direct read-only SQL oracle, not DataTools/renderer output."""
import json,sqlite3,sys
from pathlib import Path
con=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
def totals(start,end,store=None,product=None):
 clause='date BETWEEN ? AND ?';args=[start,end]
 for field,value in [('store_id',store),('product_id',product)]:
  if value:clause+=' AND '+field+'=?';args.append(value)
 sql='SELECT SUM(amount_cents), SUM(CASE WHEN amount_cents>0 THEN qty WHEN amount_cents<0 THEN -qty ELSE 0 END), COUNT(DISTINCT CASE WHEN amount_cents>0 THEN order_id END) FROM sales_clean WHERE '+clause
 row=con.execute(sql,args).fetchone()
 return dict(sql=sql,params=args,net_revenue=(row[0] or 0)/100,qty=row[1] or 0,orders=row[2])
a=totals('2026-06-01','2026-06-07','S03');b=totals('2026-06-08','2026-06-14','S03')
h2=totals('2026-06-18','2026-06-18','S02','P06');h3=totals('2026-08-01','2026-08-31',None,'P21');h5=totals('2026-08-03','2026-08-03','S05');h6=totals('2026-08-17','2026-08-19','S02')
payment_sql="SELECT payment, COUNT(DISTINCT CASE WHEN amount_cents>0 THEN order_id END), SUM(amount_cents)/100.0 FROM sales_clean WHERE date='2026-08-03' AND store_id='S05' GROUP BY payment"
prices=con.execute("SELECT date, amount_cents/100.0/qty FROM sales_clean WHERE product_id='P06' AND amount_cents>0 AND qty>0 ORDER BY date DESC LIMIT 1").fetchone()
result=dict(H01=dict(a=a,b=b,delta=b['net_revenue']-a['net_revenue'],pct=round((b['net_revenue']-a['net_revenue'])/a['net_revenue']*100,2)),H02=dict(actual=h2,target_source='KB-023: 当天牛肉poke 目标销量 120 份',goal=120,delta=h2['qty']-120),H03=dict(actual=h3,target_source='KB-028: 首月（8 月 1 日至 8 月 31 日）全门店合计目标销量 900 杯',goal=900,delta=h3['qty']-900),H04=dict(latest=prices,table_price=con.execute("SELECT unit_price FROM products WHERE product_id='P06'").fetchone()[0]),H05=dict(total=h5,payment_sql=payment_sql,rows=con.execute(payment_sql).fetchall()),H06=h6)
assert (b['net_revenue'],h2['qty'],h3['qty'],h5['orders'],h5['net_revenue'],h6['net_revenue'])==(3630,125,689,27,973,0)
Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('Independent SQL: six business expectations matched')
