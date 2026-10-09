from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

html = (ROOT / "maintenance.html").read_text(encoding="utf-8")
js = (ROOT / "assets/js/maintenance.js").read_text(encoding="utf-8")
css = (ROOT / "assets/css/main.css").read_text(encoding="utf-8")
loc = (ROOT / "assets/js/localization-static.js").read_text(encoding="utf-8")
home = (ROOT / "index.html").read_text(encoding="utf-8")
matrix = json.loads((ROOT / "config/update_matrix.json").read_text(encoding="utf-8"))

assert 'body data-page="maintenance"' in html
assert 'data-maintenance-summary' in html
assert 'data-maintenance-attention' in html
assert 'data-maintenance-table' in html
assert 'data-maintenance-rules' in html
assert 'assets/js/maintenance.js?v=' in html

# Home keeps its status shortcut and shared navigation exposes the maintenance tab.
assert 'href="maintenance.html" data-home-updated' in home
common = (ROOT / "assets/js/common.js").read_text(encoding="utf-8")
assert "key: 'maintenance', label: 'Data Status', href: 'maintenance.html'" in common

# Dashboard computes current freshness from deployed repository metadata rather than
# relying on the static 4.4B status snapshot or on GitHub Actions artifacts.
assert "config/update_matrix.json" in js
assert "entry.data_path" in js
assert "data/state/update-status.json" not in js
assert "fetch(path, { cache: 'no-cache' })" in js
assert "stale_after_hours" in js
assert "ageHours <= staleAfter" in js
assert "ageHours <= staleAfter * 1.25" in js

# Read-only browser contract: local GETs only, no mutation endpoints or repository writes.
for forbidden in ["fetch('http", 'fetch("http', "method: 'POST'", 'method: "POST"', "git push", "git commit", "promote_production"]:
    assert forbidden not in js, forbidden

# Desktop dashboard table is intentionally fixed-width to avoid unnecessary horizontal scrolling.
assert '.table-wrap--maintenance { overflow-x: hidden; }' in css
assert '.data-table--maintenance {' in css
assert 'table-layout: fixed;' in css

# VI/EN support exists for the new page.
assert "maintenance: {" in loc
assert "maintenance: MAINTENANCE" in loc
assert "Trạng thái dữ liệu" in loc
assert "Trạng thái dữ liệu · chỉ đọc" in loc

# Every source-backed matrix dataset resolves to a real repository file.
source_entries = [entry for entry in matrix["datasets"] if entry.get("data_path")]
assert len(matrix["datasets"]) == 10
assert len(source_entries) == 8
for entry in source_entries:
    assert (ROOT / entry["data_path"]).exists(), entry["data_path"]

print("Phase 4.4D maintenance dashboard tests PASS")
