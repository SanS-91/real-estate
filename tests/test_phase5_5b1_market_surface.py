from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
market=(ROOT/'assets/js/market.js').read_text(encoding='utf-8')
html=(ROOT/'market.html').read_text(encoding='utf-8')
css=(ROOT/'assets/css/main.css').read_text(encoding='utf-8')
listing=json.loads((ROOT/'data/mock/market/listing-observations.json').read_text(encoding='utf-8'))
canonical=json.loads((ROOT/'data/mock/market/observations.json').read_text(encoding='utf-8'))
macro=json.loads((ROOT/'data/processed/macro/observations.json').read_text(encoding='utf-8'))

assert 'assets/js/market.js' in html
assert 'assets/css/main.css?v=5.5C1' in html
assert 'assets/js/localization-dynamic.js?v=5.5C1' in html

assert 'Verified ASP</th>' in market
assert 'Asking range</th>' in market
assert '1Y trend</th>' in market
assert 'function priceLayerControls()' in market
assert "data-price-layer=\"verified\"" in market
assert "data-price-layer=\"listing\"" in market
assert "state.priceLayer = ['verified','listing'].includes(priceLayer) ? priceLayer : 'listing';" in market
assert "renderRangeSeries('market-overview-price'" in market
assert "renderRangeSeries('market-pricing'" in market
assert 'Latest Listing Snapshot' in market
assert 'Latest Verified Snapshot' in market
assert 'Khoảng giá chào bán theo từng dự án (tin đăng; không phải giao dịch).' in market
assert 'Không nối thành xu hướng thời gian.' in market

assert '.segmented-control.market-price-layer' in css
assert '.data-table--market-projects' in css

rows=listing['data']
latest={}
for row in sorted(rows,key=lambda x:(x['project_id'],x['observation_date'])):
    latest[row['project_id']]=row
priced=[x for x in latest.values() if x.get('asking_price_low_vnd_per_m2') is not None and x.get('asking_price_high_vnd_per_m2') is not None]
assert len(rows)>=12
assert len(latest)==12
assert len(priced)==8
assert canonical['record_count']==len(canonical['data']) and canonical['record_count']>=7
assert macro['record_count']==18

print('Phase 5.5B.1 Market Surface Integration tests PASS')
