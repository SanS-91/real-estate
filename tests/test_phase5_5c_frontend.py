from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'market.html').read_text(encoding='utf-8')
market=(ROOT/'assets/js/market.js').read_text(encoding='utf-8')
history=(ROOT/'assets/js/history-engine.js').read_text(encoding='utf-8')
css=(ROOT/'assets/css/main.css').read_text(encoding='utf-8')
prod=json.loads((ROOT/'data/mock/market/listing-observations.json').read_text(encoding='utf-8'))
candidate=json.loads((ROOT/'data/candidate/market/listing-observations.json').read_text(encoding='utf-8'))

assert 'assets/js/market.js' in html
assert 'assets/js/history-engine.js?v=5.5C1' in html
assert 'assets/css/main.css?v=5.5C1' in html
assert 'assets/js/localization-dynamic.js?v=5.5C1' in html
assert 'function listingHistoryHTML(project)' in market
assert 'function renderListingHistoryChart(projectId)' in market
assert 'Listing Price History' in market
assert 'listingMarketSeries' in history and 'listingMarketDelta' in history
assert '.chart-frame--drawer' in css
assert prod['record_count']==len(prod['data'])>=12
assert candidate['data']==[]
print('Phase 5.5C frontend contract tests PASS')
