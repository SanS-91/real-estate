from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
market=(ROOT/"assets/js/market.js").read_text(encoding="utf-8")
html=(ROOT/"market.html").read_text(encoding="utf-8")
css=(ROOT/"assets/css/main.css").read_text(encoding="utf-8")

assert 'intelligence-context.js?v=6.0' in html
assert 'function projectIntelligence(project)' in market
assert 'includeMacroContext:true' in market
assert "'usd-vnd-central-rate'" in market
assert "'credit-growth-ytd'" in market
assert 'function projectIntelligenceSummaryHTML(intel)' in market
assert 'function projectLegalEvidenceHTML(intel, project)' in market
assert 'function projectInfrastructureEvidenceHTML(intel)' in market
assert 'function projectContextHTML(intel)' in market
assert 'Legal topic-relevant docs' in market
assert 'Regional Market &amp; Macro Context' in market
assert 'Topic relevance is a research shortcut only.' in market
assert 'Regional market and macro rows are contextual evidence only' in market
assert 'id="project-context"' in market
assert 'href="#project-context"' in market

# Project detail must use the shared query for the evidence collections.
assert 'const intelligence = projectIntelligence(project);' in market
assert 'intelligence?.direct?.marketObservations' in market
assert 'intelligence?.direct?.listingObservations' in market
assert 'projectLegalEvidenceHTML(intelligence, project)' in market
assert 'projectInfrastructureEvidenceHTML(intelligence)' in market

# Shared News UI performs module-level filtering while dossier still sees all articles.
assert 'allArticles: []' in market
assert 'articles: payloadData(articles), allArticles: payloadData(articles)' in market
assert 'MarketNewsUI.render' in market
assert 'allArticles: payloadData(articles)' in market
assert 'articles:data.allArticles' in market

# New dossier surfaces are styled responsively.
assert '.project-intelligence-counts' in css
assert '.project-context-grid' in css
assert '.project-evidence-list' in css

print("Phase 6.1 project intelligence deepening tests PASS")
