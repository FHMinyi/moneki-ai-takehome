"""Hand-calculated expectations; no imports from production code."""
import argparse
import json
from urllib.request import urlopen
from urllib.parse import urlencode

p=argparse.ArgumentParser();p.add_argument('--base-url', required=True);p.add_argument('--empty', action='store_true');a=p.parse_args()
observations={}
def get(path):
    value=json.load(urlopen(a.base_url+path));observations[path]=value;return value
health=get('/api/health');quality=get('/api/data_quality');stores=get('/api/stores')
assert health['llm_mode']=='mock'
assert [s['store_id'] for s in stores['stores']]==['X11','X22']
assert [s['store_name'] for s in stores['stores']]==['替换·河畔店','替换·山麓店']
period=dict(start=None,end=None) if a.empty else dict(start='2027-01-02',end='2027-01-05')
assert health['data_period']==quality['data_period']==period
report=quality['cleaning_report']
assert health['valid_sales_rows']==report['kept_rows']==(0 if a.empty else 5)
assert report['raw_rows']==(0 if a.empty else 11)
assert report['kept_sales_rows']==(0 if a.empty else 3)
assert report['kept_refund_rows']==(0 if a.empty else 1)
assert report['removed_rows']==(0 if a.empty else 6)
assert list(report['removed'].values())==([0]*6 if a.empty else [1]*6)
# 20.01 + 5 + 30.02 - 3.01 = 52.02; 2 orders; 26.01 aov; 2+1+3-1 = 5 qty.
cases=[({},[52.02,3.01,2,26.01,5],[25.01,0,30.02,-3.01],
        [('Y93','限定新点心',30.02,3),('Y91','桂花新饮',17,1),('Y92','杂粮新碗',5,1)]),
       ({'store_id':'X11'},[22,3.01,1,22,2],[25.01,0,0,-3.01],
        [('Y91','桂花新饮',17,1),('Y92','杂粮新碗',5,1)]),
       ({'store_id':'X22'},[30.02,0,1,30.02,3],[0,0,30.02,0],
        [('Y93','限定新点心',30.02,3),('Y92','杂粮新碗',0,0)])]
for filters,values,days,products in cases:
    params=urlencode(dict(start='2027-01-02',end='2027-01-05',**filters))
    summary=get('/api/metrics/summary?'+params);daily=get('/api/metrics/daily?'+params);top=get('/api/metrics/top-products?'+params)
    assert [summary[k] for k in ('net_revenue','refund_amount','orders','aov','qty')]==([0,0,0,None,0] if a.empty else values)
    assert [d['date'] for d in daily['days']]==[f'2027-01-0{i}' for i in range(2,6)]
    assert [d['net_revenue'] for d in daily['days']]==([0]*4 if a.empty else days)
    assert round(sum(d['net_revenue'] for d in daily['days']),2)==summary['net_revenue']
    assert [(r['product_id'],r['product_name'],r['net_revenue'],r['qty']) for r in top['products']]==([] if a.empty else products)
print(json.dumps(dict(passed=True,kind='empty' if a.empty else 'replacement',observations=observations),ensure_ascii=False,indent=2))
