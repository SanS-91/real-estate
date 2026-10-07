from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
projects = json.loads((ROOT / 'data/mock/market/projects.json').read_text(encoding='utf-8'))['data']
topics = json.loads((ROOT / 'data/mock/legal/topics.json').read_text(encoding='utf-8'))['data']
infra = json.loads((ROOT / 'data/mock/infrastructure/projects.json').read_text(encoding='utf-8'))['data']
production = json.loads((ROOT / 'data/processed/macro/observations.json').read_text(encoding='utf-8'))['data']
search = (ROOT / 'assets/js/search.js').read_text(encoding='utf-8')
common = (ROOT / 'assets/js/common.js').read_text(encoding='utf-8')
market = (ROOT / 'assets/js/market.js').read_text(encoding='utf-8')
legal = (ROOT / 'assets/js/legal.js').read_text(encoding='utf-8')
loc = (ROOT / 'assets/js/localization-dynamic.js').read_text(encoding='utf-8')

valid_topics = {x['id'] for x in topics}
assert len(projects) == 8
assert all(p.get('related_legal_topic_ids') for p in projects)
assert all(set(p['related_legal_topic_ids']) <= valid_topics for p in projects)
assert all(p.get('related_infrastructure_ids') for p in projects[:2])
assert any(i.get('related_real_estate_project_ids') for i in infra)

assert "['productionMacro', DataStore.getProcessedMacroObservations]" in search
assert 'latestMacroMap' in search
assert 'related_legal_topic_ids' in search
assert 'related_real_estate_project_ids' in search
assert 'Unable to load the integrated search datasets.' in search
assert 'demo search datasets' not in search
assert 'structured demo research database' not in common
assert len(production) == 15

assert 'Legal Research Topics' in market
assert 'Open portfolio' in market
assert 'legal.html?view=documents&topic=' in market
assert 'Related Infrastructure' in market
assert 'Related Market Research' in legal
assert 'market.html?view=projects&project=' in legal
assert 'shared research topics only' in legal
assert 'Legal Research Topics' in loc

for name in ['index.html','market.html','legal.html','infrastructure.html','macro.html']:
    html = (ROOT / name).read_text(encoding='utf-8')
    assert 'assets/js/common.js?v=4.3E' in html
    assert 'assets/js/search.js?v=4.3E' in html
    assert 'assets/js/localization-static.js?v=4.3E' in html
    assert 'assets/js/localization-dynamic.js?v=4.3E' in html

print('Phase 4.3E integrated search and cross-link tests PASS')
