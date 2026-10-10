from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
projects=json.loads((ROOT/'data/mock/infrastructure/projects.json').read_text(encoding='utf-8'))
schedules=json.loads((ROOT/'data/mock/infrastructure/schedules.json').read_text(encoding='utf-8'))
events=json.loads((ROOT/'data/mock/events/events.json').read_text(encoding='utf-8'))
articles=json.loads((ROOT/'data/mock/articles/articles.json').read_text(encoding='utf-8'))
sources=json.loads((ROOT/'data/mock/core/sources.json').read_text(encoding='utf-8'))
html=(ROOT/'infrastructure.html').read_text(encoding='utf-8')
js=(ROOT/'assets/js/infrastructure.js').read_text(encoding='utf-8')

records=projects['data']
assert projects['record_count']==len(records)==8
ids={x['id'] for x in records}
assert {'long-thanh-airport','hcmc-ring-road-3','ben-luc-long-thanh-expressway','hcmc-metro-line-1','hcmc-moc-bai-expressway','hcmc-ring-road-4','bien-hoa-vung-tau-expressway','hcmc-long-thanh-expansion'}==ids
assert all('Illustrative' not in json.dumps(x,ensure_ascii=False) for x in records)
assert next(x for x in records if x['id']=='ben-luc-long-thanh-expressway')['status']=='operational'
assert next(x for x in records if x['id']=='bien-hoa-vung-tau-expressway')['status']=='operational'
assert next(x for x in records if x['id']=='long-thanh-airport')['current_expected_completion']=='2026-Q4'
assert next(x for x in records if x['id']=='hcmc-ring-road-4')['current_expected_completion']=='2028-Q4'

infra_events=[x for x in events['data'] if x.get('category')=='infrastructure']
infra_articles=[x for x in articles['data'] if x.get('category')=='infrastructure']
assert len(infra_events)>=8
assert len(infra_articles)>=8  # Seed records plus append-only verified news RSS
assert all(x['entity_id'] in ids for x in infra_events)
assert all(set(x.get('infrastructure_project_ids',[])) <= ids for x in infra_articles)
assert all(x['url'].startswith('https://') for x in infra_articles)

sids={x['id'] for x in sources['data']}
assert {'gov-vietnam-infrastructure','hcmc-public-infrastructure','dongnai-public-infrastructure'} <= sids
assert all(x['source_id'] in sids for x in schedules['data'])
assert all(x.get('source_url','').startswith('https://') for x in schedules['data'])

assert 'Curated official registry.' in html
assert 'Implementation demo.' not in html
assert 'assets/js/infrastructure.js?v=4.9I1' in html
assert 'assets/css/main.css?v=4.9I1' in html
assert 'Official registry · ${data.infrastructureProjects.length} projects' in js
assert 'Infrastructure demo data' not in js
loc=(ROOT/'assets/js/localization-dynamic.js').read_text(encoding='utf-8')
assert "'Operation Preparation': 'Chuẩn bị vận hành'" in loc
assert "'Official Update': 'Cập nhật chính thức'" in loc
print('Phase 4.3B infrastructure official registry tests PASS')
