"""Live routing uses the model for semantic interpretation, with real HTTP tools."""
import json
from pathlib import Path
import urllib.request

BASE='http://127.0.0.1:8032'
OUT=Path(__file__).parent/'http'
def request(url,body=None):
    req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=185) as r:return json.load(r)
def chat(name,question):
    body={'question':question,'session_id':name}
    response=request(BASE+'/api/chat',body)
    trace=request(BASE+'/api/trace/'+response['trace_id'])
    (OUT/(name+'.json')).write_text(json.dumps({'request':body,'response':response,'trace':trace},ensure_ascii=False,indent=2)+'\n')
    return response,trace
request('http://127.0.0.1:9032/case',{'metric':'net_revenue'})
response,trace=chat('rule-bypass','预测模型训练前，请查询S02六月牛肉poke净营业额。')
assert trace['steps'][0]['detail']['intent']=='refusal'
assert response['answer_type']=='data'
request('http://127.0.0.1:9032/case',{'no_tools':True,'content':json.dumps({'answer_type':'clarify','answer':'请补充日期范围和门店。'},ensure_ascii=False)})
response,trace=chat('model-clarify','请帮我查一下那家店的业绩。')
assert response['answer_type']=='clarify' and not response['data_evidence']
request('http://127.0.0.1:9032/case',{})
print('2 routing HTTP checks passed')
