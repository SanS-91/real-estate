"""Adversarial checks: history must remain publisher-specific and append-only."""
from __future__ import annotations

import copy
import importlib.util
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("market_gate", ROOT / "scripts/market_history_expansion_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

records = json.loads((ROOT / "config/market-history-expansion-20261009.json").read_text(encoding="utf-8"))["records"]
prod = json.loads((ROOT / "data/mock/market/observations.json").read_text(encoding="utf-8"))["data"]
sources = {x["id"] for x in json.loads((ROOT / "data/mock/core/sources.json").read_text(encoding="utf-8"))["data"]}
DATE = date(2026, 10, 9)
assert len(records) == 11, len(records)

new, decisions, conflicts = gate.stage(records, prod, sources, DATE)
assert not conflicts, conflicts
assert len(new) in (0, 11), len(new)
assert len({gate.key(x) for x in records}) == len(records)
assert {x["source_id"] for x in records} == {
    "cbre-vietnam-market", "cushman-wakefield-vietnam-market", "savills-vietnam-market"
}

def get(id):
    return next(x for x in records if x["id"] == id)

apt = get("obs-hcmc-apartment-2025-q1-cushman")
assert (apt["new_supply"], apt["sales_units"], apt["absorption_rate"]) == (2877, 1101, .46)
assert apt["source_url"].endswith("residential_eng.pdf")
assert apt["source_discrepancy"]["site_excerpt_value"] == 2392
assert apt["source_discrepancy"]["decision"] == "prefer-official-pdf-table"

q4 = get("obs-hcmc-apartment-2025-q4-cushman")
assert (q4["new_supply"], q4["sales_units"], q4["absorption_rate"]) == (3358, 3196, .62)
assert q4["sales_units"] / q4["new_supply"] != q4["absorption_rate"], "Publisher denominator not a launches ratio"

firsthalf = [x for x in records if x["period"] == "2025-H1"]
assert len(firsthalf) == 2 and all(x["scope_type"] == "region-segment-benchmark" for x in firsthalf)
assert sorted((x["segment_ids"][0], x["new_supply"]) for x in firsthalf) == [
    ("apartment", 1400), ("landed", 74)
]
residential = get("obs-hcmc-residential-2025-q1-cbre")
assert residential["segment_ids"] == ["residential"] and residential["new_supply"] == 408

# Published quarterly series for Cushman must be 5 apartment / 4 landed dates,
# with 2025-Q2/Q3 still explicitly missing, not synthesized.
combined = prod + new
def cw_periods(segment):
    return sorted({
        x["period"] for x in combined if x["source_id"] == "cushman-wakefield-vietnam-market"
        and x["scope_type"] == "region-segment" and x["segment_ids"] == [segment]
        and x["period_type"] == "quarter"
    })
assert cw_periods("apartment") == ["2024-Q4","2025-Q1","2025-Q4","2026-Q1","2026-Q2"]
assert cw_periods("landed") == ["2024-Q4","2025-Q1","2025-Q4","2026-Q2"]

# Re-running after promotion must not append any duplicate historical row.
again, decisions2, conflicts2 = gate.stage(records, prod + new, sources, DATE)
assert not again and not conflicts2
assert all(x["status"] == "unchanged" for x in decisions2)

# Wrong source domains and mismatched reporting levels must fail CLOSED.
tampered = copy.deepcopy(apt)
tampered["source_url"] = "https://fake-marketdata.example/quarterly"
assert "source-url-not-on-publisher-host" in gate.validate(tampered, sources, DATE)
tampered = copy.deepcopy(residential)
tampered["segment_ids"] = ["apartment"]
assert "combined-units-must-not-be-assigned-to-apartments" in gate.validate(tampered, sources, DATE)
tampered = copy.deepcopy(firsthalf[0])
tampered["scope_type"] = "region-segment"
assert "year-and-h1-must-be-benchmarks" in gate.validate(tampered, sources, DATE)
tampered = copy.deepcopy(q4)
tampered["new_supply"] = 9999
assert "metric-not-in-source-evidence-new_supply" in gate.validate(tampered, sources, DATE)
tampered = copy.deepcopy(q4)
tampered["source_date"] = "2024-12-01"
assert "publication-before-reporting-period-ended" in gate.validate(tampered, sources, DATE)
tampered = copy.deepcopy(apt)
tampered["average_asp"] = 50000000
assert "unverified-vnd-price-must-stay-null" in gate.validate(tampered, sources, DATE)

# A new number for a published quarter is quarantined as a conflict, never replaced.
if new:
    changed = copy.deepcopy(records[0])
    changed["new_supply"] += 100
    new_rows, status, blocked = gate.stage([changed], prod + records, sources, DATE)
    assert not new_rows and blocked, (status, blocked)

print("Market historical evidence gate: PASS (11 verified releases; strict preservation and idempotence)")
