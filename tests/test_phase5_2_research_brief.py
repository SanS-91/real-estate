from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
research=(ROOT/'research.html').read_text(encoding='utf-8')
js=(ROOT/'assets/js/research.js').read_text(encoding='utf-8')
css=(ROOT/'assets/css/main.css').read_text(encoding='utf-8')
production=json.loads((ROOT/'data/processed/macro/observations.json').read_text(encoding='utf-8'))['data']

assert 'assets/js/research.js' in research
assert 'assets/css/main.css' in research
assert 'assets/js/localization-dynamic.js' in research

assert 'function marketCoverage(ctx)' in js
assert 'function latestEvidence(ctx)' in js
assert 'function briefModel(contexts)' in js
assert 'function researchBriefHTML(contexts)' in js
assert 'function briefText(contexts)' in js
assert 'researchBriefHTML([ctx])' in js
assert 'researchBriefHTML(contexts)' in js
assert 'data-research-copy-brief' in js
assert 'data-research-print' in js
assert "filter(row => isRealSource(row.source_id))" in js
assert "(row.source_ids || []).some(isRealSource)" in js
assert "IntelligenceContext.query({" in js

assert 'average_asp =' not in js
assert 'sales_units =' not in js
assert 'absorption_rate =' not in js
assert 'No synthetic score or better/worse ranking is used.' in js
assert 'Missing fields remain blank; ASP, sales and absorption are not inferred.' in js
assert 'research relevance only' in js

assert '.research-brief__grid' in css
assert 'body.print-research-brief' in css
assert len(production)==18

print('Phase 5.2 Research Brief tests PASS')
