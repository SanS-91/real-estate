from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
matrix = json.loads((ROOT / "config/update_matrix.json").read_text(encoding="utf-8"))

rows = matrix["datasets"]
ids = [x["id"] for x in rows]
assert len(ids) == len(set(ids)) == 10
assert {x["module"] for x in rows} == {"macro", "legal", "infrastructure", "market", "home", "search"}
assert matrix["principles"]["on_source_failure"] == "retain-last-good"
assert matrix["principles"]["on_insufficient_evidence"] == "do-not-promote"
assert matrix["principles"]["on_missing_value"] == "leave-blank"
assert matrix["principles"]["synthetic_history"] is False
assert matrix["principles"]["derived_layers_create_new_facts"] is False

policy = next(x for x in rows if x["id"] == "macro-policy-rates")
assert policy["update_trigger"] == "event-driven"
assert policy["check_frequency"] == "weekly"

home = next(x for x in rows if x["id"] == "home-derived")
search = next(x for x in rows if x["id"] == "search-index")
assert home["update_mode"] == "derived"
assert search["update_mode"] == "derived-runtime"
assert len(home["depends_on"]) == 8
assert len(search["depends_on"]) == 8

print("Phase 4.4A update matrix tests PASS")
