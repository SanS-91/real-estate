from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
home=(ROOT/"index.html").read_text(encoding="utf-8")
homejs=(ROOT/"assets/js/home.js").read_text(encoding="utf-8")
maint=(ROOT/"maintenance.html").read_text(encoding="utf-8")
maintjs=(ROOT/"assets/js/maintenance.js").read_text(encoding="utf-8")
store=(ROOT/"assets/js/data-store.js").read_text(encoding="utf-8")
css=(ROOT/"assets/css/main.css").read_text(encoding="utf-8")

assert 'data-home-data-health' in home
assert 'Data Health' in home
assert 'getDataHealth' in store
assert 'function renderDataHealth()' in homejs
assert 'data-maintenance-operations' in maint
assert 'Module Operations' in maint
assert 'async function renderOperations()' in maintjs
assert '.data-health-grid' in css
assert '.maintenance-operations-grid' in css

print("Phase 5.8 data health UI tests PASS")
