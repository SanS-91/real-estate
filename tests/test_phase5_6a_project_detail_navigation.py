from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/"assets/js/market.js").read_text(encoding="utf-8")
css=(ROOT/"assets/css/main.css").read_text(encoding="utf-8")

for anchor in [
    'id="project-overview"',
    'id="project-pricing"',
    'id="project-updates"',
    'id="project-legal"',
    'id="project-infrastructure"',
    'id="project-phases"',
]:
    assert anchor in js

assert 'data-project-detail-nav' in js
assert 'function setupProjectDetailNavigation()' in js
assert "scrollIntoView({ behavior:'smooth', block:'start' })" in js
assert "IntersectionObserver" in js
assert "history.replaceState" in js
assert "window.location.hash" in js
assert ".project-detail-nav" in css
assert ".project-detail-nav a.is-active" in css
assert "scroll-margin-top" in css

print("Phase 5.6A project detail navigation tests PASS")
