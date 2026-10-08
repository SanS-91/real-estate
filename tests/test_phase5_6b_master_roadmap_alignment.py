from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
roadmap=json.loads((ROOT/"config/master-roadmap.json").read_text(encoding="utf-8"))
watch=json.loads((ROOT/"config/registry_watch.json").read_text(encoding="utf-8"))

assert roadmap["schema_version"]==1
assert [x["id"] for x in roadmap["master_phases"]]==["0","1","2","3","4","5","6","7"]
assert all(x["status"]=="complete" for x in roadmap["master_phases"][:4])
assert roadmap["master_phases"][4]["status"]=="complete"
assert roadmap["master_phases"][5]["status"]=="in-progress"

mods={x["module"]:x for x in roadmap["module_audit"]}
assert mods["market"]["collectors"]=="complete"
assert mods["macro"]["collectors"]=="complete"
assert mods["legal"]["collectors"]=="complete"
assert mods["infrastructure"]["collectors"]=="complete"

assert watch["mode"]=="assisted-registry-watch-v1"
assert watch["auto_publish"] is False
assert set(watch["modules"])=={"legal","infrastructure"}

seq=roadmap["next_sequence"]
assert [x["work_package"] for x in seq[:3]]==["5.6B","5.7","5.8"]
assert seq[-1]["work_package"]=="7.2"

doc=(ROOT/"docs/MASTER_ROADMAP.md").read_text(encoding="utf-8")
for phrase in [
    "Original 8-phase status",
    "Module architecture audit",
    "5.7 — Legal & Infrastructure Collection Completion",
    "5.8 — Unified Automation & Data Health",
    "7.2 — Optional AI Analysis Layer",
]:
    assert phrase in doc

print("Phase 5.6B master roadmap alignment tests PASS")
