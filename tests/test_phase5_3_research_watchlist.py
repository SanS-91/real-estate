from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
research=(ROOT/'research.html').read_text(encoding='utf-8')
js=(ROOT/'assets/js/research.js').read_text(encoding='utf-8')
css=(ROOT/'assets/css/main.css').read_text(encoding='utf-8')
production=json.loads((ROOT/'data/processed/macro/observations.json').read_text(encoding='utf-8'))['data']

assert 'assets/js/research.js?v=5.4M1' in research
assert 'assets/css/main.css?v=5.4M1' in research
assert 'assets/js/localization-dynamic.js?v=5.4M1' in research
assert 'data-research-watch' in research
assert 'data-watchlist-saved' in research
assert 'data-watchlist-inbox' in research
assert 'data-watchlist-review' in research

assert "WATCHLIST_KEY = 're-mi-research-watchlist-v1'" in js
assert "WATCH_REVIEW_KEY = 're-mi-research-watch-reviewed-v1'" in js
assert 'function evidenceRowsForContext(ctx)' in js
assert 'function renderWatchlist()' in js
assert 'function saveCurrentResearch()' in js
assert 'function markAllReviewed()' in js
assert 'evidenceRowsForContext(contextFor(subject)).forEach(ev => reviewed.add(ev.id))' in js
assert 'const fresh = deduped.filter(row => !reviewed.has(row.id));' in js
assert 'isRealSource(row.source_id)' in js
assert '(row.source_ids || []).find(isRealSource)' in js

assert '.research-watchlist__chips' in css
assert '.research-watchlist__count' in css
assert len(production)==18

print('Phase 5.3 Research Watchlist tests PASS')
