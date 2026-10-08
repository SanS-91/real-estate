from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
rules=json.loads((ROOT/"config/intelligence-ranking.json").read_text(encoding="utf-8"))
js=(ROOT/"assets/js/intelligence-ranking.js").read_text(encoding="utf-8")
history=(ROOT/"assets/js/history-engine.js").read_text(encoding="utf-8")
store=(ROOT/"assets/js/data-store.js").read_text(encoding="utf-8")

assert rules["max_score"]==100
assert sum(rules["weights"].values())==100
assert rules["source_priority_points"]["1"]>rules["source_priority_points"]["2"]>rules["source_priority_points"]["3"]>rules["source_priority_points"]["4"]
assert rules["purpose"].startswith("Rank attention priority")
assert any("not positive/negative impact" in x for x in rules["principles"])
assert any("Demo sources are excluded" in x for x in rules["principles"])

for fn in [
    "function sourceQuality",
    "function freshness",
    "function eventSignificance",
    "function entityRelevance",
    "function magnitude",
    "function rankOne",
    "function rankAll",
]:
    assert fn in js

assert "attention-priority-only" in js
assert "isDemoSource" in js
assert "getIntelligenceRankingRules" in store

# Legal amendment change events must retain provenance so they are rankable.
assert "source_id: row.primary_source_id" in history
assert "source_url: row.official_url" in history

print("Phase 7.0 ranking contract tests PASS")
