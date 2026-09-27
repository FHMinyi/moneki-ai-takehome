"""Controlled compliant outputs, kept separate from immutable real responses."""
import sys,json,os
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'starter'))
sys.path.insert(0,str(ROOT/'docs/verification/g3-02/review-r1-r2'))
from test_anchored_selection import anchored,duration,TEXT
from test_review import service,execute
from kbqa.document_binding import source_span

# These are test-only annotations chosen from actual retrieved evidence, not
# production question dispatch. T02-2 deliberately absent: action cannot bind.
CASES=[
 ('外卖订单多久内可以申请退款？','KB-013','24',('外卖订单','外卖订单'),('退款','退款'),duration('多久','24 小时')),
 ('有顾客问牛肉poke 里有哪些过敏原，怎么答？','KB-040','牛肉poke',('牛肉poke','牛肉poke'),('过敏原','过敏原'),TEXT),
 ('Super Souper 现在周五晚上营业到几点？','KB-062','23:00',('Super Souper','Super Souper'),('营业','营业'),{'kind':'clock','question':'几点','text':'23:00'}),
 ('三文鱼那次断供，供应商最后赔了我们多少钱？','KB-022','8,600',('三文鱼','Salmon'),('赔','credit note'),{'kind':'money','question':'多少钱','text':'CNY 8,600'}),
 ('退款在净营业额里是怎么算的？','KB-001','之和',('净营业额','净营业额'),('退款','退款'),{'kind':'rule','question':'怎么算','text':'之和'}),
 ('员工迟到多久算一次？','KB-016','15',('迟到','迟到'),('迟到','迟到'),duration('多久','15 分钟')),
 ('会员现在单笔充值满500送多少？','KB-011','60 元',('会员','会员'),('送','送'),{'kind':'money','question':'多少','text':'赠送 60 元'}),
 ('储值充值现在的赠送规则是什么？','KB-011','60 元',('储值','储值'),('赠送','赠送'),TEXT),
 ('7 月顾客投诉最集中的是什么问题？有多少条？','KB-060','12 条',('投诉','投诉'),('最集中','最集中'),{'kind':'count','question':'多少条','text':'12 条'}),
]
@pytest.mark.parametrize('case',CASES)
def test_compliant_outputs_in_actual_retrieval(service,case):
 q,doc,needle,subject,attribute,value=case
 answer,trace=execute(service,q,anchored(doc,needle,subject,attribute,value))
 assert answer.answer_type=='doc',(answer,trace.steps)
 for c in answer.citations:
  assert service.facts.index.texts[c['doc_id']][c['source_start']:c['source_end']]==c['quote']

@pytest.mark.parametrize('raw,model',[
 ('This\ncovers the value.','This covers the value.'),
 ('**净营业额** = 销售行金额之和','净营业额 = 销售行金额之和'),
 ('`amount < 0`','amount < 0'),
])
def test_formatting_is_reversible(raw,model):
 span=source_span(raw,model);assert span is not None
 assert raw[span[0]:span[1]] in raw

@pytest.mark.parametrize('raw,model',[
 ('不能退款','能退款。'),('申请退款；到账需要3天','申请退款到账需要3天'),
 ('| 商品 | 芝麻 | 奶 |','| 商品 | 奶 | 芝麻 |'),
 ('退款30元','退款60元'),('This covers it','Thiscovers it'),
])
def test_formatting_never_rewrites_semantics(raw,model):assert source_span(raw,model) is None

@pytest.mark.parametrize('value',['500 元','充值满 500 元','赠送 90 元'])
def test_generic_money_cannot_select_other_amount(service,value):
 q='会员现在单笔充值满500送多少？'
 a,t=execute(service,q,anchored('KB-011','60 元',('会员','会员'),('送','送'),{'kind':'money','question':'多少','text':value}))
 assert a.answer_type=='refusal' and not a.citations


def test_text_cannot_hide_duration(service):
 a,t=execute(service,'外卖订单多久内可以申请退款？',anchored('KB-013','24',('外卖订单','外卖订单'),('退款','退款'),{'kind':'text','question':'','text':'24 小时'}))
 assert a.answer_type=='refusal'
