"""Full valid bindings and real retrieval; free controlled responses only."""
import sys,json
from pathlib import Path
from dataclasses import replace
import pytest
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'docs/verification/g3-02/review-r1-r2'))
from test_review import service,execute
from test_anchored_selection import anchored,duration
from kbqa.service import Service
from kbqa.config import load_settings

@pytest.mark.parametrize('subject,attribute,needle',[
 (('退款','退款'),('多久','24 小时'),'24'),
 (('退款','退款'),('退款','退款'),'24'),
])
def test_arrival_cannot_use_application_window(service,subject,attribute,needle):
 a,t=execute(service,'外卖退款多久能到账？',anchored('KB-013',needle,subject,attribute,duration('多久','24 小时')))
 assert a.answer_type=='refusal' and not a.citations


def test_function_word_cannot_be_subject(service):
 a,t=execute(service,'外卖订单多久内可以退款？',anchored('KB-011','30',('内','内'),('多久','30 天'),duration('多久','30 天')))
 assert a.answer_type=='refusal' and not a.citations

@pytest.mark.parametrize('text',[
 '外卖退款不需要顾客出示身份证。请问还需要核对什么？',
 '门店退款收取手续费。请补充日期范围。',
 '本店支持无条件退回储值余额，请问哪家门店？',
])
def test_clarify_free_text_cannot_deliver_policy(service,text):
 a,t=execute(service,'外卖退款需要身份证吗？',json.dumps({'answer_type':'clarify','answer':text}),search=False)
 assert a.answer_type=='clarify' and not a.citations and not a.data_evidence
 assert text not in a.answer
 assert all(v not in a.answer for v in ['身份证','手续费','无条件'])
 assert any(s['step']=='clarification_state' for s in t.steps)


def test_typed_clarify_preserves_useful_fields(service):
 a,t=execute(service,'请查经营指标',json.dumps({'answer_type':'clarify','missing_fields':['date_range','store']}),search=False)
 assert a.answer_type=='clarify' and a.answer=='请补充日期范围和门店。'


@pytest.mark.parametrize('name,action,other', [('星砂订单','签收','复核'),('云帆工单','归档','分派')])
def test_same_dimension_different_actions_replacement(tmp_path,name,action,other):
 kb=tmp_path/'kb';kb.mkdir()
 (kb/'KB-987.md').write_text(f'# {name}时限\n\n{name}{action}须在43分钟内完成。\n\n{name}{other}须在89分钟内完成。')
 s=Service(replace(load_settings(),kb_dir=kb,var_dir=tmp_path/'var',llm_api_key='',llm_base_url='',llm_model=''));s.rebuild()
 q=f'{name}多久能{action}？'
 wrong,t=execute(s,q,anchored('KB-987','89',(name,name),('多久','89分钟'),duration('多久','89分钟')))
 assert wrong.answer_type=='refusal' and not wrong.citations
 right,u=execute(s,q,anchored('KB-987','43',(name,name),(action,action),duration('多久','43分钟')))
 assert right.answer_type=='doc' and '43' in right.answer


def test_temporal_modifier_is_not_subject_in_new_material(tmp_path):
 kb=tmp_path/'kb';kb.mkdir();(kb/'KB-988.md').write_text('# 退款规则\n\n订阅余额退款须在89天之内提出。')
 s=Service(replace(load_settings(),kb_dir=kb,var_dir=tmp_path/'var',llm_api_key='',llm_base_url='',llm_model=''));s.rebuild()
 a,t=execute(s,'外送订单多久之内可以退款？',anchored('KB-988','89',('之内','之内'),('退款','退款'),duration('多久','89天')))
 assert a.answer_type=='refusal' and not a.citations
 assert any('duration_modifier_cannot_be_subject' in str(x) for x in t.steps)

@pytest.mark.parametrize('payload',[
 {'answer_type':'clarify','missing_fields':['store'],'answer':'本店不需要身份证。'},
 {'answer_type':'clarify','missing_fields':['unsupported_policy']},
 {'answer_type':'clarify','missing_fields':['store','store']},
 {'answer_type':'clarify','missing_fields':[]},
])
def test_clarify_rejects_free_claims_and_unknown_fields(service,payload):
 from kbqa.llm import LLMError
 with pytest.raises(LLMError):execute(service,'门店规定',json.dumps(payload),search=False)
