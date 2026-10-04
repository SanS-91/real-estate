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

# Regression cases based on current public page shapes observed in Oct-2026.
def test_live_page_shapes_v2():
    nso_landing = '<a href="/du-lieu-va-so-lieu-thong-ke/2026/10/chi-so-gia-tieu-dung-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-chin-quy-iii-va-9-thang-nam-2026/">Chỉ số giá tiêu dùng, chỉ số giá vàng và chỉ số giá đô la Mỹ tháng Chín, quý III và 9 tháng năm 2026 Ngày đăng: 03/10/2026 Kỳ tham chiếu: 9/2026</a>'
    assert '/2026/10/' in discover_nso_cpi_url(nso_landing, 'https://www.nso.gov.vn/cpi-vi/')

    nso_detail = '<html><body>Kỳ tham chiếu: 9/2026 Ngày đăng: 03/10/2026 Chỉ số giá tiêu dùng (CPI) tháng 9/2026 tăng 0,62% so với tháng trước, chủ yếu do... So với tháng 12/2025, CPI tháng Chín tăng 4,2%; tăng 5,08% so với cùng kỳ năm trước. Lạm phát cơ bản tháng 9/2026 tăng 0,11% so với tháng trước và tăng 4,45% so với cùng kỳ năm trước.</body></html>'
    vals = {x['indicator_id']: x['value'] for x in parse_nso_cpi(nso_detail, 'https://nso.example', NOW)}
    assert vals['cpi-mom'] == 0.62
    assert vals['cpi-yoy'] == 5.08
    assert vals['core-cpi-yoy'] == 4.45

    sjc_flat = '<html><body>13:44 03/10/2026 (ĐVT: ngàn đồng/ lượng) Hồ Chí Minh Vàng SJC 1L, 10L, 1KG 140,500 143,500</body></html>'
    vals = {x['indicator_id']: x['value'] for x in parse_sjc_gold(sjc_flat, 'https://sjc.example', NOW)}
    assert vals['sjc-gold-bar-buy'] == 140_500_000
    assert vals['sjc-gold-bar-sell'] == 143_500_000

    vietcap_listing = '<a href="/en/research-center/macroeconomics">Macroeconomics</a><a href="/en/research-center/macro-update-q2-2026-gdp-growth-reaches-8-4">Macro Update - Q2 2026 GDP growth reaches 8.4%</a>'
    u = discover_vietcap_macro_url(vietcap_listing, 'https://www.vietcap.com.vn/en/research-center/macroeconomics')
    assert u.endswith('/macro-update-q2-2026-gdp-growth-reaches-8-4')
    vietcap_detail = '<html><head><meta property="article:published_time" content="2026-07-07T08:00:00+07:00"></head><body><h1>Macro Update - Q2 2026 GDP growth reaches 8.4%</h1>GDP expanded 8.39% YoY. CPI rose 4.69% YoY. USD/VND closed at 26,310.</body></html>'
    x = parse_vietcap_macro(vietcap_detail, 'https://vietcap.example', NOW)
    assert x['published_at'] == '2026-07-07'

# Run the additional regression cases when executed directly.
if __name__ == '__main__':
    test_live_page_shapes_v2()
    print('Live page-shape regression tests passed')
