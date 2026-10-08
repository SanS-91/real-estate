from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

home=(ROOT/'assets/js/home.js').read_text(encoding='utf-8')
loc=(ROOT/'assets/js/localization-dynamic.js').read_text(encoding='utf-8')
index=(ROOT/'index.html').read_text(encoding='utf-8')
market=(ROOT/'market.html').read_text(encoding='utf-8')
infra=(ROOT/'infrastructure.html').read_text(encoding='utf-8')
macro=(ROOT/'macro.html').read_text(encoding='utf-8')
legal=(ROOT/'legal.html').read_text(encoding='utf-8')

assert 'const latestMacro = new Map();' in home
assert 'weeklyMacroSummary(row, data.production)' in home
assert 'formatQuarterPeriod(current.period)' in home
assert 'Corroborated production observation from the approved source set.' in loc
assert 'Verified production observation from the approved official source.' in loc
assert 'Current master status' in loc
assert 'Curated registry ·' in loc
assert 'Bank Funding Growth YTD ·' in loc
assert 'Published quarterly new-supply observations' in loc

assert 'assets/js/localization-dynamic.js?v=5.0R1' in index
assert 'assets/js/localization-dynamic.js?v=5.5C1' in market
for page in (infra,macro,legal):
    assert 'assets/js/localization-dynamic.js?v=5.0R1' in page
assert 'assets/js/home.js?v=4.9.1' in index

print('Phase 4.9.1 UI polish tests PASS')
