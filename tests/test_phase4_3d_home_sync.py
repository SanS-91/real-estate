from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))

today = load('data/mock/home/today.json')
changes = load('data/mock/home/changes.json')
weekly = load('data/mock/home/weekly.json')
indicators = load('data/mock/home/indicators.json')
macro = load('data/processed/macro/observations.json')
projects = load('data/mock/market/projects.json')
legal = load('data/mock/legal/documents.json')
infra = load('data/mock/infrastructure/projects.json')
index = (ROOT / 'index.html').read_text(encoding='utf-8')
home_js = (ROOT / 'assets/js/home.js').read_text(encoding='utf-8')
components = (ROOT / 'assets/js/components.js').read_text(encoding='utf-8')
loc_static = (ROOT / 'assets/js/localization-static.js').read_text(encoding='utf-8')

assert today['is_mock'] is False
assert changes['is_mock'] is False
assert weekly['is_mock'] is False
assert indicators['is_mock'] is False
assert indicators['fallback_only'] is True
assert all(x['display_value'] == '—' for x in indicators['data'])

by_cat = {x['category']: x for x in today['data']}
assert by_cat['market']['count'] == len(projects['data']) == 8
assert by_cat['legal']['count'] == len(legal['data']) == 9
assert by_cat['infrastructure']['count'] == len(infra['data']) == 8
assert by_cat['macro']['count'] == len(macro['data']) == 15

joined = '\n'.join([
    json.dumps(today, ensure_ascii=False),
    json.dumps(changes, ensure_ascii=False),
    json.dumps(weekly, ensure_ascii=False),
    index,
])
for banned in ['Sample township', 'Illustrative pricing', 'Sample land regulation', 'Implementation demo.', 'Mixed data mode.']:
    assert banned not in joined

assert 'Integrated curated data.' in index
assert '<h2 id="today-title">Latest</h2>' in index
assert 'policy-refinancing-rate' in home_js
assert 'Integrated data · 4 curated modules' in home_js
assert 'group.count_label' in components
assert "['#today-title', 'Latest', 'Mới nhất']" in loc_static
assert 'assets/js/home.js?v=4.3D' in index
assert 'assets/js/localization-dynamic.js?v=4.3E' in index

# Weekly recap contains only observations inside 01-07 Oct 2026 in this curated build.
assert [x['date_label'] for x in weekly['data']] == ['05 Oct', '05 Oct', '03 Oct', '01 Oct']

# No fabricated sales metric in Home change summary.
market_change = next(x for x in changes['data'] if x['category'] == 'market')
assert 'Sales remain blank' in market_change['summary']

print('Phase 4.3D Home sync tests PASS')
