from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
js = (ROOT / "assets/js/legal.js").read_text(encoding="utf-8")
css = (ROOT / "assets/css/main.css").read_text(encoding="utf-8")
html = (ROOT / "legal.html").read_text(encoding="utf-8")

assert "documentTable(latest, { compact: true })" in js
assert "table-wrap--legal-overview" in js
assert "data-table--legal-overview" in js
assert ".table-wrap--legal-overview { overflow-x: hidden; }" in css
assert "min-width: 0;" in css
assert "table-layout: fixed;" in css
assert "td:nth-child(2) { width: 40%; }" in css
assert 'assets/css/main.css?v=4.3A4' in html
assert 'assets/js/legal.js?v=4.3A4' in html

# Normal legal table must remain wide for the full Documents view.
assert ".data-table--legal { min-width: 1120px; }" in css

print("Phase 4.3A.2 legal overview compact-table tests PASS")
