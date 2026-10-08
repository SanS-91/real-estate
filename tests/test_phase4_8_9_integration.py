from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

pages={
 'index.html':'assets/js/home.js?v=4.9.1',
 'macro.html':'assets/js/macro.js?v=4.9I1',
 'legal.html':'assets/js/legal.js?v=4.9I1',
 'infrastructure.html':'assets/js/infrastructure.js?v=4.9I1',
 'market.html':'assets/js/market.js?v=5.5B1',
}
for page,script in pages.items():
    text=(ROOT/page).read_text(encoding='utf-8')
    assert 'assets/js/history-engine.js?v=4.9I1' in text
    assert script in text
    expected_css = 'assets/css/main.css?v=5.5A1' if page == 'market.html' else 'assets/css/main.css?v=4.9I1'
    assert expected_css in text

home=(ROOT/'assets/js/home.js').read_text(encoding='utf-8')
legal=(ROOT/'assets/js/legal.js').read_text(encoding='utf-8')
infra=(ROOT/'assets/js/infrastructure.js').read_text(encoding='utf-8')
market=(ROOT/'assets/js/market.js').read_text(encoding='utf-8')
macro=(ROOT/'assets/js/macro.js').read_text(encoding='utf-8')
engine=(ROOT/'assets/js/history-engine.js').read_text(encoding='utf-8')

assert 'HistoryEngine.buildIntelligence' in home
assert 'HistoryEngine?.legalTimeline' in legal
assert 'HistoryEngine?.infrastructureTimeline' in infra
assert 'HistoryEngine?.marketProjectHistory' in market
assert 'HistoryEngine.macroSeries' in macro
assert 'window.HistoryEngine' in engine
print('Phase 4.8/4.9 frontend integration tests PASS')
