from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/"assets/js/market.js").read_text(encoding="utf-8")
css=(ROOT/"assets/css/main.css").read_text(encoding="utf-8")

assert "'project-detail'" in js
assert "function renderProjectDetail()" in js
assert "function projectDetailListingHistory(project)" in js
assert "function relatedInfrastructureForProject(project)" in js
assert 'market.html?view=project-detail&id=' in js
assert "Official &amp; Research Updates" in js
assert "Legal Research" in js
assert "Infrastructure" in js
assert "Data Sources" in js
assert "market-project-listing-history" in js
assert "target=\"_blank\" rel=\"noopener noreferrer\"" in js
assert ".project-detail-grid" in css
assert ".project-detail-facts" in css
assert ".project-detail-link-list" in css

print("Phase 5.6 project detail view tests PASS")
