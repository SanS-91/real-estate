from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "infrastructure.html").read_text(encoding="utf-8")
js = (ROOT / "assets/js/infrastructure.js").read_text(encoding="utf-8")
css = (ROOT / "assets/css/main.css").read_text(encoding="utf-8")
loc = (ROOT / "assets/js/localization-dynamic.js").read_text(encoding="utf-8")

assert "assets/css/main.css?v=4.3B1" in html
assert "assets/js/infrastructure.js?v=4.3B1" in html
assert "assets/js/localization-dynamic.js?v=4.3B1" in html

assert "market-layout--infra-overview" in js
assert "table-wrap--infra-overview" in js
assert "data-table--infra-overview" in js
assert "Current situation" in js
assert "infrastructureStatusBadge(project.status)" in js
assert "'hcmc': 'TPHCM'" in js
assert "'dong-nai': 'Đồng Nai'" in js
assert "'binh-duong': 'Bình Dương'" in js
assert "app:language-changed" in js

assert ".market-layout--infra-overview" in css
assert "grid-template-columns: minmax(0, 3fr) minmax(260px, 1fr);" in css
assert ".table-wrap--infra-overview" in css and "overflow-x: hidden;" in css
assert ".data-table--infra-overview" in css and "table-layout: fixed;" in css
assert ".data-table--infra { min-width: 1080px; }" in css  # full Projects view remains wide

assert "'Current situation': 'Tình hình hiện tại'" in loc
assert "'land clearance': 'giải phóng mặt bằng'" in loc
assert "'quarter': 'quý'" in loc
assert r"Official registry · (\d+) projects" in loc

print("Phase 4.3B.1 infrastructure UI cleanup tests PASS")
