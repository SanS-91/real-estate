from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / "assets/css/main.css").read_text(encoding="utf-8")
html = (ROOT / "legal.html").read_text(encoding="utf-8")

assert "font-size: 12px;" in css
assert ".data-table--legal-overview th { font-size: 10.5px; }" in css
assert ".data-table--legal-overview .document-number { font-size: 10.75px; }" in css
assert ".data-table--legal-overview .table-subtext { font-size: 10px; }" in css
assert "assets/css/main.css?v=4.3STACK1" in html
assert ".table-wrap--legal-overview { overflow-x: hidden; }" in css

print("Phase 4.3A.3 legal overview font test PASS")
