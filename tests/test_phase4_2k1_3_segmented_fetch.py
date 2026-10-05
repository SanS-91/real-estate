from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from collectors.base import fetch_html_segmented

class FakeResponse:
    def __init__(self, url, status, payload, content_range=None):
        self.url=url; self.status_code=status; self.content=payload
        self.headers={'Content-Type':'text/html'}
        if content_range: self.headers['Content-Range']=content_range
        self.encoding='utf-8'; self.apparent_encoding='utf-8'
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(self.status_code)

class FakeSession:
    def __init__(self, payload): self.payload=payload; self.calls=[]
    def get(self, url, timeout=None, headers=None, allow_redirects=True):
        self.calls.append(dict(headers or {}))
        rg=(headers or {}).get('Range')
        if not rg: return FakeResponse(url,200,self.payload)
        a,b=rg.replace('bytes=','').split('-'); a=int(a); b=int(b)
        b=min(b,len(self.payload)-1)
        part=self.payload[a:b+1]
        return FakeResponse(url,206,part,f'bytes {a}-{b}/{len(self.payload)}')

def test_segmented_fetch_reassembles_document():
    payload=(b'policy rates 4.5 3.0 5.0 | '*5000)
    s=FakeSession(payload)
    out=fetch_html_segmented('https://example.test/doc',max_bytes=len(payload)+100,segment_bytes=10000,segment_retries=2,session=s)
    assert out.text.encode()==payload
    assert len(s.calls) > 2
    assert all(c.get('Accept-Encoding')=='identity' for c in s.calls)

def test_sbv_archive_uses_segmented_strategy():
    import json
    cfg=json.loads((ROOT/'config/live_sources.json').read_text(encoding='utf-8'))['sources']
    s=next(x for x in cfg if x['key']=='sbv-policy-archive')
    assert s['fetch_strategy']=='segmented-range'
    assert s['segment_bytes'] <= 1_000_000
    assert s['max_bytes'] >= 8_000_000

if __name__=='__main__':
    test_segmented_fetch_reassembles_document(); test_sbv_archive_uses_segmented_strategy(); print('Phase 4.2K.1.3 segmented fetch tests passed')
