from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / 'assets/css/main.css').read_text(encoding='utf-8')
legal = (ROOT / 'legal.html').read_text(encoding='utf-8')
infra = (ROOT / 'infrastructure.html').read_text(encoding='utf-8')
assert '.market-layout--legal-overview,\n.market-layout--infra-overview {' in css
assert 'grid-template-columns: minmax(0, 1fr);' in css
assert 'assets/css/main.css?v=4.3STACK1' in legal
assert 'assets/css/main.css?v=4.3STACK1' in infra
assert 'market-layout--legal-overview' in (ROOT/'assets/js/legal.js').read_text(encoding='utf-8')
assert 'market-layout--infra-overview' in (ROOT/'assets/js/infrastructure.js').read_text(encoding='utf-8')
print('Phase 4.3 stacked overview layout tests PASS')
