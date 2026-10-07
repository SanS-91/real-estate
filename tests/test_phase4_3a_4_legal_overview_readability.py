from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / "assets/css/main.css").read_text(encoding="utf-8")
js = (ROOT / "assets/js/legal.js").read_text(encoding="utf-8")
html = (ROOT / "legal.html").read_text(encoding="utf-8")

assert "market-layout--legal-overview" in js
assert "market-panel--legal-documents" in js
assert "market-panel--legal-timeline" in js
assert "grid-template-columns: minmax(0, 2.15fr) minmax(250px, .72fr);" in css
assert ".market-panel--legal-documents .section-header .eyebrow { font-size: 12px; }" in css
assert ".market-panel--legal-documents .section-header .section-title { font-size: 19px; }" in css
assert "font-size: 12px;" in css
assert ".data-table--legal-overview th { font-size: 10.5px; }" in css
assert ".data-table--legal-overview .document-number { font-size: 10.75px; }" in css
assert ".data-table--legal-overview .table-subtext { font-size: 10px; }" in css
assert "assets/css/main.css?v=4.3STACK1" in html
assert "assets/js/legal.js?v=4.3E" in html
assert ".table-wrap--legal-overview { overflow-x: hidden; }" in css
print("Phase 4.3A.4 legal overview readability tests PASS")
