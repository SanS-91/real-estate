from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
research=(ROOT/'research.html').read_text(encoding='utf-8')
js=(ROOT/'assets/js/research.js').read_text(encoding='utf-8')
market=(ROOT/'assets/js/market.js').read_text(encoding='utf-8')
market_html=(ROOT/'market.html').read_text(encoding='utf-8')
production=json.loads((ROOT/'data/processed/macro/observations.json').read_text(encoding='utf-8'))['data']

assert 'data-research-entity="0"' in research
assert 'data-research-entity="1"' in research
assert 'data-research-entity="2"' in research
assert 'data-research-share' in research
assert 'assets/js/research.js?v=5.5B1' in research
assert 'assets/css/main.css?v=5.5A1' in research
assert 'assets/js/localization-dynamic.js?v=5.5A1' in research

assert "const state = { type: 'project', ids: [] };" in js
assert "url.searchParams.set('ids', state.ids.join(','))" in js
assert "slice(0,3)" in js
assert 'function renderCompare(contexts)' in js
assert 'function compareTable(contexts)' in js
assert 'function compareShared(contexts)' in js
assert 'No synthetic scoring' in js
assert 'do not establish legal applicability' in js
assert 'Common context, not used to score subjects.' in js

assert 'research.html?type=project&ids=${encodeURIComponent(project.id)}' in market
assert 'research.html?type=developer&ids=${encodeURIComponent(dev.id)}' in market
assert 'assets/js/market.js?v=5.5B1' in market_html
assert len(production)==18

print('Phase 5.1 research compare tests PASS')
