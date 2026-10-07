from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
projects=json.loads((ROOT/'data/mock/market/projects.json').read_text(encoding='utf-8'))
devs=json.loads((ROOT/'data/mock/core/developers.json').read_text(encoding='utf-8'))
obs=json.loads((ROOT/'data/mock/market/observations.json').read_text(encoding='utf-8'))
phases=json.loads((ROOT/'data/mock/market/project-phases.json').read_text(encoding='utf-8'))
arts=json.loads((ROOT/'data/mock/articles/articles.json').read_text(encoding='utf-8'))
sources=json.loads((ROOT/'data/mock/core/sources.json').read_text(encoding='utf-8'))
html=(ROOT/'market.html').read_text(encoding='utf-8')
js=(ROOT/'assets/js/market.js').read_text(encoding='utf-8')

assert projects['record_count']==12
assert {x['id'] for x in projects['data']} == {'izumi-city','waterpoint','akari-city','mizuki-park','the-global-city','eaton-park','elysian','the-privia','vinhomes-grand-park','the-9-stellars','celesta-gold','essensia-parkway'}
assert all('Illustrative' not in x.get('summary','') for x in projects['data'])
assert all(x.get('primary_source_id') for x in projects['data'])
assert all(x.get('official_url','').startswith('http') for x in projects['data'])
assert devs['record_count']==9
assert 'ecopark' not in {x['id'] for x in devs['data']}
assert all(x.get('primary_source_id') for x in devs['data'])
assert obs['record_count']==7
assert not any(x.get('source_id','').startswith('demo-') for x in obs['data'])
assert any(x['id']=='obs-hcmc-apartment-2026-q2-cbre' and x['new_supply']==850 for x in obs['data'])
assert any(x['id']=='obs-elysian-2025-07' and x['average_asp']==68000000 for x in obs['data'])
assert any(x['id']=='obs-the-privia-2024' and x['absorption_rate']==1.0 for x in obs['data'])
market_articles=[x for x in arts['data'] if x.get('category')=='market']
assert len(market_articles)==6
assert not any(x.get('source_id','').startswith('demo-') for x in market_articles)
source_ids={x['id'] for x in sources['data']}
for sid in ['nam-long-official','masterise-homes-official','gamuda-land-official','khang-dien-official','vinhomes-official','sonkim-land-official','keppel-real-estate-vietnam','phu-long-official','nomura-real-estate-vietnam','cbre-vietnam-market','savills-vietnam-market']:
    assert sid in source_ids
assert 'Implementation demo.' not in html
assert 'Curated market registry.' in html
assert 'market.js?v=4.3E' in html
assert 'Demo data' not in js
assert 'No missing project price is estimated.' in js
assert "scope_type === 'region-segment-benchmark'" in js
# Publication/source-date precision guards
obs_by_id = {x["id"]: x for x in obs['data']}
assert obs_by_id["obs-hcmc-apartment-2025-savills-benchmark"]["source_date"] == "2026-04-21"
assert obs_by_id["obs-the-privia-2024"]["source_date"] == "2024-11-18"

article_by_id = {x["id"]: x for x in market_articles}
assert article_by_id["article-market-savills-2025"]["published_at"].startswith("2026-04-21")
assert article_by_id["article-market-privia-2024"]["published_at"].startswith("2024-11-18")

# Do not convert "nearly/over" disclosures into fake exact totals.
project_by_id = {x["id"]: x for x in projects['data']}
assert project_by_id["akari-city"]["planned_units"] is None
assert "More than 5,000" in project_by_id["akari-city"]["known_units_note"]
assert project_by_id["mizuki-park"]["planned_units"] is None
assert project_by_id["essensia-parkway"]["planned_units"] is None
assert "74 units" in project_by_id["essensia-parkway"]["source_discrepancy_note"]
assert "75 low-rise" in project_by_id["essensia-parkway"]["source_discrepancy_note"]

phase_by_id = {x["id"]: x for x in phases['data']}
assert phase_by_id["waterpoint-solaria-rise"]["planned_units"] is None
assert "Nearly 700" in phase_by_id["waterpoint-solaria-rise"]["known_units_note"]
assert phase_by_id["akari-phase-1"]["planned_units"] is None
assert "Nearly 2,000" in phase_by_id["akari-phase-1"]["known_units_note"]

print('Phase 4.3C curated market registry tests PASS')
