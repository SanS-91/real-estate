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
assert today['fallback_only'] is True
assert changes['fallback_only'] is True
assert weekly['fallback_only'] is True
assert indicators['is_mock'] is False
assert indicators['fallback_only'] is True
assert all(x['display_value'] == '—' for x in indicators['data'])

by_cat = {x['category']: x for x in today['data']}
assert by_cat['market']['count'] == len(projects['data']) == 12
assert by_cat['legal']['count'] == len(legal['data']) == 16
assert by_cat['infrastructure']['count'] == len(infra['data']) == 8
assert by_cat['macro']['count'] == 18
assert macro['record_count'] == len(macro['data'])
assert len(macro['data']) == by_cat['macro']['count']

joined = '\n'.join([
    json.dumps(today, ensure_ascii=False),
    json.dumps(changes, ensure_ascii=False),
    json.dumps(weekly, ensure_ascii=False),
    index,
])
for banned in ['Sample township', 'Illustrative pricing', 'Sample land regulation', 'Implementation demo.', 'Mixed data mode.']:
    assert banned not in joined

assert 'Integrated curated data.' in index
assert '<h2 id="today-title">Today</h2>' in index
assert 'policy-refinancing-rate' in home_js
assert 'Integrated data · 4 curated modules' in home_js
assert 'group.count_label' in components
assert "['#today-title', 'Today', 'Hôm nay']" in loc_static
assert 'assets/js/home.js?v=' in index
assert 'loadCanonicalHomeData' in home_js
assert 'buildTodayGroups(data)' in home_js
assert 'buildChanges(data)' in home_js
assert 'buildWeekly(data)' in home_js
assert 'buildTopDevelopments(data)' in home_js
assert 'data-home-top-developments' in index
assert 'assets/js/localization-dynamic.js?v=5.0R1' in index

# Weekly recap contains only observations inside 01-07 Oct 2026 in this curated build.
assert [x['date_label'] for x in weekly['data']] == ['07 Oct', '07 Oct', '03 Oct', '01 Oct']

# No fabricated sales metric in Home change summary.
assert any(x['category'] == 'macro' and '25,638' in x['title'] for x in changes['data'])

print('Phase 4.3D Home sync tests PASS')
