from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
listing=json.loads((ROOT/'data/mock/market/listing-observations.json').read_text(encoding='utf-8'))
projects=json.loads((ROOT/'data/mock/market/projects.json').read_text(encoding='utf-8'))['data']
canonical=json.loads((ROOT/'data/mock/market/observations.json').read_text(encoding='utf-8'))
production=json.loads((ROOT/'data/processed/macro/observations.json').read_text(encoding='utf-8'))
research=(ROOT/'assets/js/research.js').read_text(encoding='utf-8')
market=(ROOT/'assets/js/market.js').read_text(encoding='utf-8')
research_html=(ROOT/'research.html').read_text(encoding='utf-8')
market_html=(ROOT/'market.html').read_text(encoding='utf-8')

rows=listing['data']
assert listing['record_count']==len(rows)>=12
latest={}
for row in sorted(rows,key=lambda x:(x['project_id'],x['observation_date'])):
    latest[row['project_id']]=row
baseline={x['project_id']:x for x in rows if x['observation_date']=='2026-10-08'}
assert len(baseline)==12
assert set(latest) == {x['id'] for x in projects}
assert all(x['market_layer']=='listing-asking' for x in rows)
assert all(x['source_id']=='batdongsan-com-vn' for x in rows)
assert all(x['volatile_metrics']['use_in_primary_kpi'] is False for x in rows)

full=[x for x in latest.values() if x.get('coverage_status')=='full']
partial=[x for x in latest.values() if x.get('coverage_status')=='partial']
priced=[x for x in latest.values() if x.get('asking_price_low_vnd_per_m2') is not None and x.get('asking_price_high_vnd_per_m2') is not None]
assert len(full)==8
assert len(partial)==4
assert len(priced)==8

by=baseline  # Historical baseline remains auditable after later reviewed snapshots.
assert by['waterpoint']['asking_price_low_vnd_per_m2']==37_100_000
assert by['akari-city']['asking_price_high_vnd_per_m2']==66_100_000
assert by['mizuki-park']['asking_price_change_1y_pct']==0.191
assert by['eaton-park']['asking_price_high_vnd_per_m2']==209_500_000
assert by['elysian']['popular_area_low_sqm']==34
assert by['the-privia']['asking_price_low_vnd_per_m2']==61_500_000
assert by['vinhomes-grand-park']['volatile_metrics']['listing_count']==868
assert by['the-9-stellars']['asking_price_low_vnd_per_m2'] is None
assert by['celesta-gold']['product_price_ranges'][0]['product']=='1BR'
assert by['essensia-parkway']['asking_price_change_1y_pct']==-0.052
assert by['izumi-city']['confidence']=='mapped-partial'

# Partial coverage must remain blank instead of inventing project-level asking ranges.
for pid in ['izumi-city','the-9-stellars','celesta-gold','essensia-parkway']:
    assert by[pid]['asking_price_low_vnd_per_m2'] is None
    assert by[pid]['asking_price_high_vnd_per_m2'] is None

assert canonical['record_count']==len(canonical['data']) and canonical['record_count']>=7
assert not any(x.get('source_id')=='batdongsan-com-vn' for x in canonical['data'])
assert len(production['data'])==18

assert 'listing.coverage_status === \'partial\'' in research
assert 'listingCoverage(ctx).priced' in research
assert 'row.coverage_status === \'partial\'' in market
assert 'assets/js/research.js' in research_html
assert 'assets/js/market.js' in market_html

print('Phase 5.5B Listing Market Coverage tests PASS')
