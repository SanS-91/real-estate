from pathlib import Path
import json, re

ROOT=Path(__file__).resolve().parents[1]
rules=json.loads((ROOT/"config/intelligence-ranking.json").read_text(encoding="utf-8"))
sources=json.loads((ROOT/"data/mock/core/sources.json").read_text(encoding="utf-8"))["data"]
engine=(ROOT/"assets/js/intelligence-ranking.js").read_text(encoding="utf-8")
doc=(ROOT/"docs/PHASE7_0_INTELLIGENCE_RANKING.md").read_text(encoding="utf-8")

weights=rules["weights"]
assert set(weights)=={"source_quality","freshness","event_significance","entity_relevance","change_magnitude"}
assert sum(weights.values())==rules["max_score"]==100
assert all(isinstance(v,(int,float)) and v>=0 for v in weights.values())

priority=rules["source_priority_points"]
assert priority["1"] > priority["2"] > priority["3"] > priority["4"] > priority["default"]
assert priority["1"] <= weights["source_quality"]

fresh=rules["freshness_points"]
finite=[x for x in fresh if x["max_age_days"] is not None]
assert finite==sorted(finite,key=lambda x:x["max_age_days"])
assert [x["points"] for x in fresh]==sorted([x["points"] for x in fresh],reverse=True)
assert fresh[-1]["max_age_days"] is None and fresh[-1]["points"]==0
assert all(x["points"]<=weights["freshness"] for x in fresh)

tiers=rules["tiers"]
mins=[x["min_score"] for x in tiers]
assert mins==sorted(mins,reverse=True)
assert mins[-1]==0
assert len({x["id"] for x in tiers})==len(tiers)

for category,table in rules["category_type_points"].items():
    assert table["default"] <= weights["event_significance"]
    assert all(v<=weights["event_significance"] for v in table.values())

entity=rules["entity_relevance"]
assert entity["tracked_entity_cap"]<=weights["entity_relevance"]

mag=rules["magnitude_rules"]
assert mag["schedule_change_points"]<=weights["change_magnitude"]
assert mag["legal_amendment_points"]<=weights["change_magnitude"]
assert mag["event_importance_cap"]<=weights["change_magnitude"]
assert all(x["points"]<=weights["change_magnitude"] for x in mag["percent_change"])

allowed_priorities={1,2,3,4}
prod=[x for x in sources if x.get("active") and not x["id"].startswith("demo-")]
assert prod
assert all(x.get("source_priority") in allowed_priorities for x in prod)

for phrase in [
    "attention priority",
    "investment score",
    "Missing evidence produces zero points",
    "AI is not used",
]:
    assert phrase.lower() in doc.lower()

for field in [
    "attention_score",
    "attention_tier",
    "attention_label",
    "ranking_components",
    "ranking_evidence",
    "ranking_semantics:'attention-priority-only'",
]:
    assert field in engine

assert "source_quality:source.points" in engine
assert "freshness:fresh.points" in engine
assert "event_significance:significance.points" in engine
assert "entity_relevance:relevance.points" in engine
assert "change_magnitude:change.points" in engine

print("Phase 7.0A ranking contract audit PASS")
