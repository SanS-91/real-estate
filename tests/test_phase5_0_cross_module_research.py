from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding='utf-8'))

projects=load('data/mock/market/projects.json')['data']
developers=load('data/mock/core/developers.json')['data']
regions=load('data/mock/core/regions.json')['data']
infra=load('data/mock/infrastructure/projects.json')['data']
legal=load('data/mock/legal/documents.json')['data']
topics=load('data/mock/legal/topics.json')['data']
production=load('data/processed/macro/observations.json')['data']

research=(ROOT/'research.html').read_text(encoding='utf-8')
js=(ROOT/'assets/js/research.js').read_text(encoding='utf-8')
common=(ROOT/'assets/js/common.js').read_text(encoding='utf-8')

assert 'research.html' in common
assert "{ key: 'research', label: 'Research'" in common
assert 'data-research-type' in research
assert 'data-research-entity' in research
assert 'assets/js/research.js?v=5.5B1' in research
assert 'assets/js/common.js?v=5.0R1' in research
assert 'assets/js/localization-dynamic.js?v=5.5A1' in research

for page in ['index.html','market.html','legal.html','infrastructure.html','macro.html','maintenance.html']:
    text=(ROOT/page).read_text(encoding='utf-8')
    assert 'assets/js/common.js?v=5.0R1' in text
    expected_loc = 'assets/js/localization-dynamic.js?v=5.5C1' if page == 'market.html' else 'assets/js/localization-dynamic.js?v=5.0R1'
    assert expected_loc in text

pmap={x['id']:x for x in projects}
imap={x['id']:x for x in infra}
dmap={x['id']:x for x in developers}
rmap={x['id']:x for x in regions}
tmap={x['id']:x for x in topics}

izumi=pmap['izumi-city']
assert 'dong-nai' in izumi['region_ids']
assert 'nam-long' in izumi.get('developer_ids',[]) or izumi.get('lead_developer_id')=='nam-long'
assert len(izumi.get('related_infrastructure_ids',[])) >= 1
assert all(x in imap for x in izumi.get('related_infrastructure_ids',[]))
assert all(x in tmap for x in izumi.get('related_legal_topic_ids',[]))

namlong_projects=[p for p in projects if 'nam-long' in p.get('developer_ids',[]) or p.get('lead_developer_id')=='nam-long']
assert len(namlong_projects) >= 3

dongnai_projects=[p for p in projects if 'dong-nai' in p.get('region_ids',[])]
assert len(dongnai_projects) >= 1
dongnai_infra=[x for x in infra if 'dong-nai' in x.get('region_ids',[])]
assert len(dongnai_infra) >= 1

assert len(production)==18
assert 'Research relevance, not legal advice.' in research
assert 'do not determine legal applicability' in js
assert 'not project-specific causality' in js
assert 'average_asp =' not in js
assert 'sales_units =' not in js
assert 'absorption_rate =' not in js

print('Phase 5.0 cross-module research tests PASS')
