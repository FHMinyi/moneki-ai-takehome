"""Explicit fixture annotations for the controlled model, NEVER production logic.

Migrates the old evidence-ID-only fixtures to the reviewed selection protocol.
Separate hand-annotated adversarial HTTP cases test conflicts/omissions.
"""
import sys,re
from pathlib import Path

def binding_for(question,e):
 sys.path.insert(0,str(Path(__file__).parent/'review-r1-r2'))
 from test_anchored_selection import PUBLIC_BINDINGS,TEXT,duration
 from test_document_binding import QUESTIONS
 specs={QUESTIONS[k]:v for k,v in PUBLIC_BINDINGS.items()}
 if question in specs:subject,attribute,value=specs[question]
 elif e['doc_id'] in ('KB-013','KB-012'):
  subject=('外卖','外卖') if '外卖' in question else ('退款','退款');attribute=('退款','退款')
  marker=next((v for v in ('时限','几小时','多久') if v in question),'')
  m=re.search(r'\d+\s*(?:小时|天)',e['quote'])
  value=duration(marker,m.group(0)) if marker and m else TEXT
 elif e['doc_id'] in ('KB-010','KB-011'):
  subject=('会员','会员');attribute=('充值','充值')
  marker='多少' if '多少' in question else '';m=re.search(r'赠送\s*(\d+\s*元)',e['quote'])
  value={'kind':'value','question':marker,'text':m.group(1)} if marker and m else TEXT
 elif e['doc_id']=='KB-040':
  subject=('Beef Poke','牛肉poke') if 'Beef Poke' in question else ('牛肉poke','牛肉poke')
  attribute=('过敏原','过敏原') if '过敏原' in question else ('花生','芝麻');value=TEXT
 elif e['doc_id'] in ('KB-971','KB-972'):
  subject=('翡翠饭','翡翠饭');attribute=('配送时限','配送时限');m=re.search(r'\d+分钟',e['quote'])
  value=duration('时限',m.group(0)) if m else TEXT
 elif e['doc_id']=='KB-060':
  subject=('顾客','顾客');attribute=('投诉','投诉');value={'kind':'count','question':'多少条','text':'12 条'}
 else:
  # Negative legacy fixtures intentionally cannot provide a supported binding.
  subject=(question[:2],e['quote'][:2]);attribute=(question[:2],e['quote'][:2]);value=TEXT
 def anchor(pair):
  q,text=pair
  if text in e['quote']:source='quote'
  elif any(text in c['quote'] for c in e['context']):source=next(i for i,c in enumerate(e['context']) if text in c['quote'])
  elif text in e['metadata'].get('title',''):source='title'
  else:source='quote'
  return {'question':q,'source':source,'text':text}
 return {'subject':[anchor(subject)],'attribute':[anchor(attribute)],'value':value}
