from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))

sources=load('data/mock/core/sources.json')
listing=load('data/mock/market/listing-observations.json')
comparables=load('data/mock/market/listing-comparables.json')
canonical=load('data/mock/market/observations.json')
production=load('data/processed/macro/observations.json')
research=(ROOT/'assets/js/research.js').read_text(encoding='utf-8')
market=(ROOT/'assets/js/market.js').read_text(encoding='utf-8')
store=(ROOT/'assets/js/data-store.js').read_text(encoding='utf-8')
research_html=(ROOT/'research.html').read_text(encoding='utf-8')
market_html=(ROOT/'market.html').read_text(encoding='utf-8')

source={x['id']:x for x in sources['data']}['batdongsan-com-vn']
assert source['source_type']=='property-listing-portal'
assert source['source_priority']==4
assert 'Never treated as transaction price' in source['notes']

assert listing['record_count']>=1
row={x['project_id']:x for x in listing['data']}['the-global-city']
assert row['market_layer']=='listing-asking'
assert row['asking_price_low_vnd_per_m2']==112_000_000
assert row['asking_price_high_vnd_per_m2']==143_500_000
assert row['asking_price_change_1y_pct']==-0.189
assert row['popular_area_low_sqm']==51
assert row['popular_area_high_sqm']==215
assert row['volatile_metrics']['listing_count']==234
assert row['volatile_metrics']['project_views_7d']==1254
assert row['volatile_metrics']['use_in_primary_kpi'] is False
assert 'not executed transaction price' in row['methodology_note']

ranges={x['product']:x for x in row['product_price_ranges']}
assert ranges['1BR']['low_vnd']==6_150_000_000
assert ranges['2BR']['high_vnd']==11_000_000_000
assert ranges['3BR']['high_vnd']==17_910_000_000

assert comparables['record_count']==12
assert all(x['anchor_project_id']=='the-global-city' for x in comparables['data'])
assert all(x['capture_type']=='map-label-snapshot' for x in comparables['data'])
assert any(x['comparable_name']=='Eaton Park' and x['asking_price_vnd_per_m2']==149_100_000 for x in comparables['data'])
assert any(x['comparable_name']=='The Global City' and x['asking_price_vnd_per_m2']==125_400_000 for x in comparables['data'])

# Listing intelligence stays separate from canonical research/official market observations.
assert canonical['record_count']==len(canonical['data']) and canonical['record_count']>=7
assert not any(x.get('source_id')=='batdongsan-com-vn' for x in canonical['data'])
assert len(production['data'])==18

assert 'getListingObservations' in store
assert 'getListingComparables' in store
assert 'function listingMarketHTML(ctx)' in research
assert 'Listing-market coverage' in research
assert 'function listingMarketDrawerHTML(project)' in market
assert 'not transaction price' in market

assert 'assets/js/data-store.js?v=5.5A1' in research_html
assert 'assets/js/research.js' in research_html
assert 'assets/css/main.css' in research_html
assert 'assets/js/data-store.js?v=5.5A1' in market_html
assert 'assets/js/market.js' in market_html
assert 'assets/css/main.css?v=5.5C1' in market_html

print('Phase 5.5A Listing Market Intelligence tests PASS')
