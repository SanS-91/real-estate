from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
research=(ROOT/'research.html').read_text(encoding='utf-8')
js=(ROOT/'assets/js/research.js').read_text(encoding='utf-8')
css=(ROOT/'assets/css/main.css').read_text(encoding='utf-8')
obs=json.loads((ROOT/'data/mock/market/observations.json').read_text(encoding='utf-8'))['data']
production=json.loads((ROOT/'data/processed/macro/observations.json').read_text(encoding='utf-8'))['data']

assert 'assets/js/research.js' in research
assert 'assets/css/main.css' in research
assert 'assets/js/localization-dynamic.js' in research

assert 'function marketSingleHTML(ctx)' in js
assert 'function marketCompareHTML(contexts)' in js
assert 'function supportingContextHTML(ctx)' in js
assert 'Market Comparison Matrix' in js
assert 'Market Performance & Positioning' in js
assert 'Coverage: Price ' in js
assert "Formatters.unitValue('vnd-per-m2'" in js

single=js.index('function renderSingle(ctx)')
compare=js.index('function renderCompare(contexts)')
render=js.index('function render()', compare)
single_block=js[single:compare]
compare_block=js[compare:render]

assert single_block.index('marketSingleHTML(ctx)') < single_block.index('supportingContextHTML(ctx)')
assert single_block.index('supportingContextHTML(ctx)') < single_block.index('researchBriefHTML([ctx])')
assert compare_block.index('marketCompareHTML(contexts)') < compare_block.index('compareShared(contexts)')
assert compare_block.index('compareShared(contexts)') < compare_block.index('researchBriefHTML(contexts)')

assert 'Cross-module Coverage' not in compare_block
assert 'No synthetic scoring' in js
assert 'not project-specific causality' in js or 'not project-specific causality'.replace(' ',' ') in js

project_obs=[x for x in obs if x.get('project_id')]
assert len(project_obs)==2
assert any(x.get('average_asp') is not None for x in project_obs)
assert any(x.get('sales_units') is not None for x in project_obs)
assert len(production)==18

assert '.research-market-primary' in css
assert '.research-context-grid' in css
assert '.research-macro-grid--compact' in css

print('Phase 5.4 Market-first Research tests PASS')
