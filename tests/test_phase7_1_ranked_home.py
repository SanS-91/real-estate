from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
index=(ROOT/"index.html").read_text(encoding="utf-8")
home=(ROOT/"assets/js/home.js").read_text(encoding="utf-8")
components=(ROOT/"assets/js/components.js").read_text(encoding="utf-8")
roadmap=(ROOT/"config/master-roadmap.json").read_text(encoding="utf-8")

assert '<h2 id="today-title">Latest Updates</h2>' in index
assert 'data-home-top-developments' in index
assert 'class="home-more-history"' in index
assert 'assets/js/intelligence-ranking.js?v=7.0' in index
assert 'assets/js/intelligence-surfaces.js?v=7.1' in index
assert 'assets/js/home.js?v=7.1&home4J1=1' in index

for fn in [
    "function homeReferenceDate()",
    "function buildRankableCandidates(data)",
    "function rankedCandidates(data)",
    "function rankedChangeCandidates(data)",
    "function formatRankedItem(item,data)",
    "function buildTopDevelopments(data)",
    "async function renderTopDevelopments()",
]:
    assert fn in home

assert "IntelligenceRanking.rankAll" in home
assert "IntelligenceSurfaces?.withinDays" in home
assert "IntelligenceSurfaces?.thisWeek" in home
assert "IntelligenceSurfaces?.topDevelopments" in home
assert "IntelligenceSurfaces?.topPerCategory" in home
assert "attention_label" in home
assert "attention_score" in home
assert 'class="importance-label"' in components
assert '"work_package": "7.1"' in roadmap

print("Phase 7.1 ranked intelligence Home integration tests PASS")
