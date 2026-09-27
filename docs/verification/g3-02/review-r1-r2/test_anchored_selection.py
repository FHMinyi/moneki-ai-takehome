"""Same-response support annotations are controlled inputs, not model proof."""
import json,sys
from pathlib import Path
from dataclasses import replace
import pytest
sys.path.insert(0,str(Path(__file__).parent))
from test_review import execute,service,ROOT
from kbqa.service import Service
from kbqa.config import load_settings
from kbqa.document_evidence import DocumentEvidence
from kbqa.trace import Trace


def anchored(doc,needle,subject,attribute,value):
 def selection(result):
  e=next(e for e in result['evidence'] if e['doc_id']==doc and needle in e['quote'])
  def anchor(pair):
   question,text=pair
   if text in e['quote']:source='quote'
   elif any(text in c['quote'] for c in e['context']):source=next(i for i,c in enumerate(e['context']) if text in c['quote'])
   elif text in e['metadata'].get('title',''):source='title'
   else:raise AssertionError(('anchor missing',text,e))
   return {'question':question,'source':source,'text':text}
  binding={'subject':[anchor(subject)],'attribute':[anchor(attribute)],'value':value}
  return json.dumps({'answer_type':'doc','facts':[{'evidence_id':e['evidence_id'],'binding':binding}]})
 return selection

def duration(q,text):return {'kind':'duration','question':q,'text':text}
TEXT={'kind':'text','question':'','text':''}

@pytest.mark.parametrize('q,doc,needle,subject,attribute,value',[
 ('外卖订单多久内可以退款？','KB-013','堂食订单须当场',('外卖订单','堂食订单'),('退款','退款'),TEXT),
 ('办理外卖退款应当出示什么身份证件？','KB-014','工牌',('外卖','员工'),('身份证件','工牌'),TEXT),
 ('员工迟到申诉多久能处理完？','KB-016','15',('迟到申诉','迟到'),('处理','记'),duration('多久','15 分钟')),
 ('外卖订单多久内可以退款？','KB-011','30',('外卖订单','储值本金'),('退款','退回'),duration('多久','30 天')),
])
def test_conflicting_anchored_subject_or_attribute(service,q,doc,needle,subject,attribute,value):
 a,t=execute(service,q,anchored(doc,needle,subject,attribute,value))
 assert a.answer_type=='refusal' and not a.citations
 assert any(s['step']=='document_binding_rejected' for s in t.steps)

@pytest.mark.parametrize('q,doc,needle,subject,attribute,value',[
 ('外卖订单多久内可以退款？','KB-013','24',('外卖订单','外卖订单'),('退款','退款'),duration('多久','24 小时')),
 ('外卖订单退款时限？','KB-013','24',('外卖订单','外卖订单'),('退款','退款'),duration('时限','24 小时')),
 ('外卖订单几小时内退款？','KB-013','24',('外卖订单','外卖订单'),('退款','退款'),duration('几小时','24 小时')),
 ('2026-06-14外卖订单多久内可以退款？','KB-012','7 天',('外卖订单','外卖订单'),('退款','退款'),duration('多久','7 天')),
 ('Beef Poke过敏原？','KB-040','牛肉poke',('Beef Poke','牛肉poke'),('过敏原','过敏原'),TEXT),
])
def test_supported_same_response_anchors(service,q,doc,needle,subject,attribute,value):
 a,t=execute(service,q,anchored(doc,needle,subject,attribute,value))
 assert a.answer_type=='doc',a
 assert any(c['doc_id']==doc for c in a.citations)
 assert any(s['step']=='document_binding' for s in t.steps)


def test_omitting_appeal_qualifier_cannot_relabel_attendance(service):
 q='迟到申诉多久？'
 a,t=execute(service,q,anchored('KB-016','15',('迟到','迟到'),('迟到','迟到'),duration('多久','15 分钟')))
 assert a.answer_type=='refusal' and not a.citations
 assert any('omitted_subject_qualifier' in str(s) for s in t.steps)

@pytest.mark.parametrize('fmt',['md','txt','gbk','html'])
def test_replaced_material_supports_new_fact_and_alias(tmp_path,fmt):
 kb=tmp_path/'kb';kb.mkdir()
 (kb/'KB-981.md').write_text('| 标准写法 | alias |\n|---|---|\n| 星云订单 | Nebula Order |')
 suffix='txt' if fmt=='gbk' else fmt
 for n in (37,83):
  fact=f'星云订单退款须在{n}分钟内提出。'
  body=('<h2>退款受理</h2><p>'+fact+'</p>') if fmt=='html' else fact
  (kb/('KB-982.'+suffix)).write_bytes(body.encode('gbk' if fmt=='gbk' else 'utf-8'))
  s=Service(replace(load_settings(),kb_dir=kb,var_dir=tmp_path/str(n),llm_api_key='',llm_base_url='',llm_model=''))
  s.rebuild()
  for q in ('星云订单退款多久内提出？','Nebula Order退款时限？'):
   subj='Nebula Order' if 'Nebula' in q else '星云订单'
   a,t=execute(s,q,anchored('KB-982',str(n),(subj,'星云订单'),('退款','退款'),duration('时限' if '时限' in q else '多久',f'{n}分钟')))
   assert a.answer_type=='doc' and str(n) in a.answer,a


def test_cross_clause_subject_attribute_binding_rejected(tmp_path):
 kb=tmp_path/'kb';kb.mkdir();(kb/'KB-983.md').write_text('星云订单可以开发票。木星订单退款时限为37分钟。')
 s=Service(replace(load_settings(),kb_dir=kb,var_dir=tmp_path/'var',llm_api_key='',llm_base_url='',llm_model=''))
 s.rebuild()
 a,t=execute(s,'星云订单退款时限？',anchored('KB-983','发票。木星',('星云订单','星云订单'),('退款','退款'),duration('时限','37分钟')))
 assert a.answer_type=='refusal' and not a.citations

# Explicit test annotations for the public questions; not a production answer map.
PUBLIC_BINDINGS={
 'C01':(('外卖订单','外卖订单'),('退款','退款'),duration('多久','24 小时')),
 'C02':(('牛肉poke','牛肉poke'),('过敏原','过敏原'),TEXT),
 'C03':(('Super Souper','Super Souper'),('营业','营业'),{'kind':'clock','question':'几点','text':'23:00'}),
 'C04':(('三文鱼','Salmon'),('赔','credit note'),{'kind':'money','question':'多少钱','text':'CNY 8,600'}),
 'C05':(('发票','发票'),('开','开'),TEXT),
 'C06':(('净营业额','净营业额'),('退款','退款'),{'kind':'rule','question':'怎么算','text':'之和'}),
 'C07':(('吞拿鱼三明治','吞拿鱼三明治'),('为什么','毛利率低于 35%'),{'kind':'reason','question':'为什么','text':'毛利率低于 35%'}),
 'C08':(('迟到','迟到'),('多久','15 分钟'),duration('多久','15 分钟')),
 'V01':(('活动','活动'),('活动价','活动价'),{'kind':'money','question':'活动价','text':'¥29'}),
 'V02':(('会员','会员'),('充值','充值'),{'kind':'value','question':'多少','text':'60 元'}),
}
@pytest.mark.parametrize('qid',PUBLIC_BINDINGS)
def test_original_public_questions_with_anchored_response(service,qid):
 sys.path.insert(0,str(ROOT/'docs/verification/g3-02'))
 from test_document_binding import PUBLIC_SELECTIONS,QUESTIONS
 doc,needle=PUBLIC_SELECTIONS[qid]
 a,t=execute(service,QUESTIONS[qid],anchored(doc,needle,*PUBLIC_BINDINGS[qid]))
 assert a.answer_type=='doc',(a,t.steps)

@pytest.mark.parametrize('q',[
 '外卖订单多久内可以申请退款？',
 '请问外卖订单几小时内能申请退款？',
 '麻烦说明外卖订单退款时限。',
])
def test_ordinary_functional_rephrasing_not_rejected(service,q):
 focus='几小时' if '几小时' in q else '时限' if '时限' in q else '多久'
 a,t=execute(service,q,anchored('KB-013','24',('外卖订单','外卖订单'),('退款','退款'),duration(focus,'24 小时')))
 assert a.answer_type=='doc',a


def test_omitted_channel_with_same_numeric_shape_rejected(tmp_path):
 kb=tmp_path/'kb';kb.mkdir()
 (kb/'KB-986.md').write_text('# 退款时限\n\n外送订单退款须在43分钟内提出。\n\n自取订单退款须在89分钟内提出。')
 s=Service(replace(load_settings(),kb_dir=kb,var_dir=tmp_path/'var',llm_api_key='',llm_base_url='',llm_model=''));s.rebuild()
 # Both have genuine duration values and the same head '订单'. Deliberately
 # omit the channel from the model's subject anchor; code sees explicit conflict.
 a,t=execute(s,'外送订单退款时限？',anchored('KB-986','89',('订单','订单'),('退款','退款'),duration('时限','89分钟')))
 assert a.answer_type=='refusal' and not a.citations
 assert any('explicit_subject_modifier_conflict' in str(step) for step in t.steps)
 b,u=execute(s,'外送订单退款时限？',anchored('KB-986','43',('订单','订单'),('退款','退款'),duration('时限','43分钟')))
 assert b.answer_type=='doc' and '43' in b.answer

@pytest.mark.parametrize('question',['迟到申诉多久？','迟到的申诉多久？','迟到申诉需要多久？'])
def test_omission_variants_keep_critical_qualifier(service,question):
 a,t=execute(service,question,anchored('KB-016','15',('迟到','迟到'),('多久','15 分钟'),duration('多久','15 分钟')))
 assert a.answer_type=='refusal' and not a.citations


def test_self_reported_support_boolean_not_a_binding(service):
 def final(r):
  e=next(e for e in r['evidence'] if e['doc_id']=='KB-013')
  return json.dumps({'answer_type':'doc','facts':[{'evidence_id':e['evidence_id'],'binding':{'subject_supported':True,'attribute_supported':True}}]})
 a,t=execute(service,'外卖订单多久内可以退款？',final)
 assert a.answer_type=='refusal' and not a.citations
