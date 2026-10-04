from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from collectors.nso_cpi import parse_nso_cpi, discover_nso_cpi_url
from collectors.sjc_gold import parse_sjc_gold
from collectors.sbv_central_rate import parse_sbv_central_rate
from collectors.vov_central_rate import parse_vov_central_rate, discover_vov_central_rate_url
from collectors.vietcap_macro import parse_vietcap_macro, discover_vietcap_macro_url
from collectors.vietnamplus_cpi import parse_vietnamplus_cpi, discover_vietnamplus_cpi_url
from collectors.vietnamplus_central_rate import parse_vietnamplus_central_rate, discover_vietnamplus_central_rate_url
from collectors.pnj_gold import parse_pnj_gold
from collectors.doji_gold import parse_doji_gold
from collectors.baonghean_gold import parse_baonghean_gold
from collectors.thoibaonganhang_central_rate import parse_thoibaonganhang_central_rate, discover_thoibaonganhang_central_rate_url
from collectors.vietnamnet_gold import parse_vietnamnet_gold

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


def test_vietnamplus_cpi():
    x = parse_vietnamplus_cpi(read('vietnamplus_cpi_sample.html'), 'https://vietnamplus.example/cpi', NOW)
    d = {i['indicator_id']: i for i in x}
    assert d['cpi-mom']['value'] == 0.62
    assert d['cpi-yoy']['value'] == 5.08
    assert d['core-cpi-yoy']['value'] == 4.45
    assert d['cpi-yoy']['period'] == '2026-09'

def test_vietnamplus_central_rate():
    x = parse_vietnamplus_central_rate(read('vietnamplus_central_rate_sample.html'), 'https://vietnamplus.example/fx', NOW)
    assert x[0]['value'] == 25636
    assert x[0]['source_id'] == 'vna-vietnamplus'

def test_pnj_gold():
    x = parse_pnj_gold(read('pnj_gold_sample.html'), 'https://pnj.example', NOW)
    d = {i['indicator_id']: i for i in x}
    assert d['sjc-gold-bar-buy']['value'] == 144_600_000
    assert d['sjc-gold-bar-sell']['value'] == 147_600_000

def test_doji_gold():
    x = parse_doji_gold(read('doji_gold_sample.html'), 'https://doji.example', NOW)
    d = {i['indicator_id']: i for i in x}
    assert d['sjc-gold-bar-buy']['value'] == 144_600_000
    assert d['sjc-gold-bar-sell']['value'] == 147_600_000


def test_baonghean_gold():
    x = parse_baonghean_gold(read('baonghean_gold_sample.html'), 'https://baonghean.vn/gia-vang-hom-nay/gia-vang-sjc', NOW)
    d = {i['indicator_id']: i for i in x}
    assert d['sjc-gold-bar-buy']['value'] == 140_500_000
    assert d['sjc-gold-bar-sell']['value'] == 143_500_000
    assert d['sjc-gold-bar-sell']['data_date'] == '2026-10-04'



def test_thoibaonganhang_central_rate():
    x = parse_thoibaonganhang_central_rate(read('thoibaonganhang_central_rate_sample.html'), 'https://thoibaonganhang.vn/example', NOW)
    assert x[0]['value'] == 25636
    assert x[0]['data_date'] == '2026-10-02'
    assert x[0]['source_id'] == 'banking-times-vn'
    assert x[0]['evidence_status'] == 'reported'


def test_vietnamnet_gold():
    x = parse_vietnamnet_gold(read('vietnamnet_gold_sample.html'), 'https://dantocphattrien.vietnamnet.vn/gia-vang', NOW)
    d = {i['indicator_id']: i for i in x}
    assert d['sjc-gold-bar-buy']['value'] == 140_500_000
    assert d['sjc-gold-bar-sell']['value'] == 143_500_000
    assert d['sjc-gold-bar-sell']['data_date'] == '2026-10-04'
    assert d['sjc-gold-bar-sell']['source_id'] == 'vietnamnet-gold'

def test_discovery_helpers():
    nso = '<a href="/du-lieu-va-so-lieu-thong-ke/2026/10/chi-so-gia-tieu-dung-thang-chin/">Chỉ số giá tiêu dùng tháng Chín 2026</a>'
    assert discover_nso_cpi_url(nso, 'https://www.nso.gov.vn/cpi-vi/').startswith('https://www.nso.gov.vn/')
    vov = '<a href="/thi-truong/ty-gia-usd-hom-nay-post1.vov">Tỷ giá trung tâm USD/VND hôm nay</a>'
    assert discover_vov_central_rate_url(vov, 'https://vov.vn/thi-truong/').startswith('https://vov.vn/')
    vietcap = '<a href="/en/research-center/macro-update-q3-2026">Macro Update Q3 2026</a>'
    assert discover_vietcap_macro_url(vietcap, 'https://www.vietcap.com.vn/en/research-center/').endswith('/macro-update-q3-2026')
    vp_cpi = '<a href="/nguon-cung-hang-hoa-cpi-post1139783.vnp">CPI tháng 9 tăng 0,62%</a>'
    assert discover_vietnamplus_cpi_url(vp_cpi, 'https://www.vietnamplus.vn/cpi-tag1091331.vnp').startswith('https://www.vietnamplus.vn/')
    vp_fx = '<a href="/reference-exchange-rate-bounces-back-post352944.vnp">Reference exchange rate bounces back on October 2</a>'
    assert discover_vietnamplus_central_rate_url(vp_fx, 'https://en.vietnamplus.vn/daily-reference-exchange-rate-tag9131.vnp').startswith('https://en.vietnamplus.vn/')
    bt = '<a href="/sang-210-nhnn-niem-yet-ty-gia-trung-tam-o-muc-25636-dong-188382.html">Sáng 2/10: NHNN niêm yết tỷ giá trung tâm ở mức 25.636 đồng</a>'
    assert discover_thoibaonganhang_central_rate_url(bt, 'https://thoibaonganhang.vn/ngan-hang/thi-truong-tien-te').startswith('https://thoibaonganhang.vn/')

if __name__ == '__main__':
    test_nso(); test_sjc(); test_sbv(); test_vov(); test_vietcap(); test_vietnamplus_cpi(); test_vietnamplus_central_rate(); test_pnj_gold(); test_doji_gold(); test_baonghean_gold(); test_thoibaonganhang_central_rate(); test_vietnamnet_gold(); test_discovery_helpers()
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

    vp_live = """<html><head><meta property='article:published_time' content='2026-10-04T12:03:00+07:00'></head><body><h1>Vietnam’s CPI rises 4.52% in first nine months of 2026</h1>CPI in September rose 0.62% from the previous month. September’s CPI was up 5.08% year-on-year.</body></html>"""
    vals = {x['indicator_id']: x for x in parse_vietnamplus_cpi(vp_live, 'https://en.vietnamplus.vn/example.vnp', NOW)}
    assert vals['cpi-mom']['value'] == 0.62
    assert vals['cpi-yoy']['value'] == 5.08
    assert vals['cpi-yoy']['period'] == '2026-09'

    bt_live = '<html><body><h1>Sáng 2/10: NHNN niêm yết tỷ giá trung tâm ở mức 25.636 đồng</h1><div>09:26 | 02/10/2026</div><p>Ngày 2/10, NHNN niêm yết tỷ giá trung tâm ở mức 25.636 đồng.</p></body></html>'
    bx = parse_thoibaonganhang_central_rate(bt_live, 'https://thoibaonganhang.vn/example', NOW)
    assert bx[0]['value'] == 25636 and bx[0]['data_date'] == '2026-10-02'

    vnn_live = '<html><body>Cập nhật lúc 22:38 ngày 04/10/2026 <table><tr><td>SJC</td><td>TP. Hồ Chí Minh Vàng SJC 1L, 10L, 1KG</td><td>140.500.000</td><td>143.500.000</td></tr></table></body></html>'
    gv = {x['indicator_id']:x for x in parse_vietnamnet_gold(vnn_live, 'https://dantocphattrien.vietnamnet.vn/gia-vang', NOW)}
    assert gv['sjc-gold-bar-buy']['value'] == 140_500_000
    assert gv['sjc-gold-bar-sell']['value'] == 143_500_000

# Run the additional regression cases when executed directly.
if __name__ == '__main__':
    test_live_page_shapes_v2()
    print('Live page-shape regression tests passed')
