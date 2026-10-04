from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from collectors.nso_cpi import parse_nso_cpi, discover_nso_cpi_url
from collectors.sjc_gold import parse_sjc_gold
from collectors.sbv_central_rate import parse_sbv_central_rate
from collectors.vov_central_rate import parse_vov_central_rate, discover_vov_central_rate_url
from collectors.vietcap_macro import parse_vietcap_macro, discover_vietcap_macro_url

FIX = ROOT / 'tests/fixtures'
NOW = '2026-10-04T00:00:00+00:00'

def read(name): return (FIX / name).read_text(encoding='utf-8')

def test_nso():
    x = parse_nso_cpi(read('nso_cpi_sample.html'), 'https://nso.example', NOW)
    d = {i['indicator_id']: i for i in x}
    assert d['cpi-yoy']['value'] == 5.08
    assert d['cpi-mom']['value'] == 0.62
    assert d['core-cpi-yoy']['value'] == 4.45
    assert d['cpi-yoy']['period'] == '2026-09'

def test_sjc():
    x = parse_sjc_gold(read('sjc_sample.html'), 'https://sjc.example', NOW)
    d = {i['indicator_id']: i for i in x}
    assert d['sjc-gold-bar-buy']['value'] == 140_500_000
    assert d['sjc-gold-bar-sell']['value'] == 143_500_000

def test_sbv():
    x = parse_sbv_central_rate(read('sbv_sample.html'), 'https://sbv.example', NOW)
    assert x[0]['value'] == 25636 and x[0]['evidence_status'] == 'verified'

def test_vov():
    x = parse_vov_central_rate(read('vov_sample.html'), 'https://vov.example', NOW)
    assert x[0]['value'] == 25636 and x[0]['evidence_status'] == 'reported'

def test_vietcap():
    x = parse_vietcap_macro(read('vietcap_sample.html'), 'https://vietcap.example', NOW)
    facts = {f['metric']: f['value'] for f in x['facts']}
    assert facts['cpi-yoy'] == 4.69
    assert facts['usd-vnd-market-close'] == 26310

def test_discovery_helpers():
    nso = '<a href="/du-lieu-va-so-lieu-thong-ke/2026/10/chi-so-gia-tieu-dung-thang-chin/">Chỉ số giá tiêu dùng tháng Chín 2026</a>'
    assert discover_nso_cpi_url(nso, 'https://www.nso.gov.vn/cpi-vi/').startswith('https://www.nso.gov.vn/')
    vov = '<a href="/thi-truong/ty-gia-usd-hom-nay-post1.vov">Tỷ giá trung tâm USD/VND hôm nay</a>'
    assert discover_vov_central_rate_url(vov, 'https://vov.vn/thi-truong/').startswith('https://vov.vn/')
    vietcap = '<a href="/en/research-center/macro-update-q3-2026">Macro Update Q3 2026</a>'
    assert discover_vietcap_macro_url(vietcap, 'https://www.vietcap.com.vn/en/research-center/').endswith('/macro-update-q3-2026')

if __name__ == '__main__':
    test_nso(); test_sjc(); test_sbv(); test_vov(); test_vietcap(); test_discovery_helpers()
    print('All parser/discovery tests passed')
