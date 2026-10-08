from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
css=(ROOT/'assets/css/main.css').read_text(encoding='utf-8')
loc=(ROOT/'assets/js/localization-dynamic.js').read_text(encoding='utf-8')
html=(ROOT/'market.html').read_text(encoding='utf-8')
market=(ROOT/'assets/js/market.js').read_text(encoding='utf-8')

assert '.developer-card__links { display: flex;' in css
assert "'Open Research': 'Nghiên cứu'" in loc
assert "'Disclosed qualitatively': 'Chỉ công bố định tính'" in loc
assert "^(\\d+) tracked projects$" in loc
assert 'assets/css/main.css?v=5.5A1' in html
assert 'assets/js/localization-dynamic.js?v=5.5A1' in html
assert 'developer-card__links' in market
assert 'research.html?type=developer&ids=' in market

print('Market Phase 5.1 UI polish tests PASS')
