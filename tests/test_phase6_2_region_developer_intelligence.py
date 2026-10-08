from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/"assets/js/research.js").read_text(encoding="utf-8")
css=(ROOT/"assets/css/main.css").read_text(encoding="utf-8")
html=(ROOT/"research.html").read_text(encoding="utf-8")
roadmap=json.loads((ROOT/"config/master-roadmap.json").read_text(encoding="utf-8"))

assert 'assets/js/intelligence-context.js?v=6.0' in html
assert 'IntelligenceContext.query({' in js
assert "type:state.type" in js
assert 'regionalMarketObservations:contextual.regionalMarketObservations' in js
assert 'macroContext:contextual.macroObservations' in js
assert 'infrastructureSchedules:direct.infrastructureSchedules' in js
assert 'intelligence:evidence' in js

# The old relationship implementation must no longer be duplicated in Research.
assert "let projects = [];" not in js[js.index("function contextFor(subject)"):js.index("function watchKey")]
assert "projects = data.projects.filter(project =>" not in js[js.index("function contextFor(subject)"):js.index("function watchKey")]

assert 'function subjectIntelligenceDossierHTML(ctx)' in js
assert 'Region Dossier' in js
assert 'Developer Dossier' in js
assert 'Developer Footprint' in js
assert 'Geographic Footprint' in js
assert 'Region infrastructure includes direct project links and geographic context.' in js
assert 'Portfolio metrics reflect canonically linked projects' in js
assert 'market.html?view=projects&region=' in js
assert 'market.html?view=projects&developer=' in js
assert 'research.html?type=developer&ids=' in js
assert 'research.html?type=region&ids=' in js

assert '.research-dossier-metrics' in css
assert '.research-dossier-columns' in css

status={x["work_package"]:x["status"] for x in roadmap["next_sequence"]}
# Updated later in this branch before merge.
assert status["6.0"]=="complete"
assert status["6.1"]=="complete"
assert status["6.2"]=="complete"

print("Phase 6.2 Region & Developer intelligence UI contract tests PASS")
