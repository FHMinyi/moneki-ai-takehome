"""Offline proxy budget tests: fake HTTP upstream; never calls the provider."""
import importlib.util,json,threading,urllib.request,urllib.error
from pathlib import Path
import pytest
import httpx
spec=importlib.util.spec_from_file_location('guard',Path(__file__).with_name('run_live_samples.py'))
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
@pytest.mark.parametrize('mode',['complete','missing_usage','transport','insufficient','oversize'])
def test_reserve_before_send_and_never_release_unknown(tmp_path,monkeypatch,mode):
    ledger={'chat_count':5,'chat_limit':5,'limit_cny':8,'calls':[],'billing_confirmed':False}
    if mode=='insufficient':ledger['calls']=[{'chat':1,'accounted_cny':7.9}]
    monkeypatch.setattr(g,'ledger',ledger);monkeypatch.setattr(g,'ledger_path',tmp_path/'ledger.json')
    reached=[]
    class FakeClient:
        def __init__(self,*a,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,*a,**kw):
            assert ledger['calls'][-1]['accounted_cny']==2.20
            reached.append(True)
            if mode=='transport':raise httpx.TimeoutException('offline')
            payload={'choices':[]}
            if mode=='complete':payload['usage']={'prompt_tokens':100,'completion_tokens':20}
            return httpx.Response(200,json=payload)
    monkeypatch.setattr(g.httpx,'Client',FakeClient)
    server=g.ThreadingHTTPServer(('127.0.0.1',0),g.Proxy);threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        body={'model':'deepseek-flash','max_tokens':4096,'messages':[]}
        if mode=='oversize':body['padding']='x'*250000
        request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/guard/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request) as r:status=r.status
        except urllib.error.HTTPError as e:status=e.code
    finally:server.shutdown();server.server_close()
    if mode in ('insufficient','oversize'):
        assert not reached and status in (400,402)
    else:
        assert reached
        assert ledger['calls'][-1]['accounted_cny']==(.00036 if mode=='complete' else 2.20)
