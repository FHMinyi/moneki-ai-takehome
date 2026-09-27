from pathlib import Path
import tempfile,shutil,json,time
from test_http import runtime,ROOT
work=Path(tempfile.mkdtemp(prefix='moneki-g302-browser-'))
with runtime(work,{'doc':'KB-013','needle':'24'}) as (r,serve,payload):
    shutil.copytree(ROOT/'frontend/dist',work/'frontend/dist')
    with serve() as request:
        record=r.records[-1]
        manifest={'work':str(work),'pid':record['pid'],'port':record['port'],'base':f"http://127.0.0.1:{record['port']}",'model':'controlled-only'}
        (ROOT/'docs/verification/g3-02/browser-resources.json').write_text(json.dumps(manifest,indent=2))
        print(json.dumps(manifest),flush=True)
        while True:time.sleep(1)
