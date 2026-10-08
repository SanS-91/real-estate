from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/"config/ai-analysis.json").read_text(encoding="utf-8"))
research=(ROOT/"research.html").read_text(encoding="utf-8")
js=(ROOT/"assets/js/research.js").read_text(encoding="utf-8")
pack=(ROOT/"assets/js/analysis-context-pack.js").read_text(encoding="utf-8")
adapter=(ROOT/"assets/js/optional-ai-analysis.js").read_text(encoding="utf-8")
store=(ROOT/"assets/js/data-store.js").read_text(encoding="utf-8")

assert cfg["enabled"] is False
assert cfg["external_requests"] is False
assert cfg["endpoint"] is None
assert cfg["same_origin_only"] is True

serialized=json.dumps(cfg).lower()
for forbidden in ["api_key","apikey","authorization","password"]:
    assert forbidden not in serialized

assert "getAIAnalysisConfig" in store
assert "assets/js/analysis-context-pack.js?v=7.2" in research
assert "assets/js/optional-ai-analysis.js?v=7.2" in research
assert "assets/js/research.js?v=7.2" in research

for phrase in [
    "function analysisPanelHTML(contexts)",
    "function buildCurrentAnalysis(contexts)",
    "data-ai-build",
    "data-ai-copy-prompt",
    "data-ai-copy-context",
    "DataStore.getAIAnalysisConfig()",
]:
    assert phrase in js

for safeguard in [
    "no_missing_value_inference",
    "legal_relevance_is_not_applicability",
    "listing_asking_is_separate_from_verified_pricing",
    "no_production_mutation",
]:
    assert safeguard in pack

assert "same_origin_only" in adapter
assert "Remote AI analysis is disabled. No network request was sent." in adapter

print("Phase 7.2 optional AI analysis integration tests PASS")
