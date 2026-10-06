from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

mapping = load("config/frontend_indicator_map.json")
assert mapping["frontend_baseline"] == "v7.2.1+4.2J3.2+4.2K4"
for iid in ["policy-refinancing-rate","policy-rediscount-rate","policy-overnight-lending-rate"]:
    assert mapping["mappings"][iid] == {"frontend_indicator_id": iid, "status": "compatible"}

processed = load("data/processed/macro/observations.json")
assert processed["record_count"] == 15
rows = processed["data"]
policy = {r["indicator_id"]: r for r in rows if r["indicator_id"].startswith("policy-")}
assert set(policy) == {"policy-refinancing-rate","policy-rediscount-rate","policy-overnight-lending-rate"}
expected = {"policy-refinancing-rate":4.5,"policy-rediscount-rate":3.0,"policy-overnight-lending-rate":5.0}
for iid,value in expected.items():
    r=policy[iid]
    assert r["value"] == value
    assert r["period"] == "2023-06-19"
    assert r["evidence_status"] == "corroborated"
    assert set(r["corroboration_source_ids"]) == {"vna-vietnamplus","banking-times-vn"}

indicators = load("data/mock/macro/indicators.json")
ids={x["id"] for x in indicators["data"]}
assert {"policy-refinancing-rate","policy-rediscount-rate","policy-overnight-lending-rate"}.issubset(ids)
assert indicators["record_count"] == len(indicators["data"])

macro=(ROOT/"assets/js/macro.js").read_text(encoding="utf-8")
for iid in expected:
    assert f"['{iid}', {{ unit: 'percent-per-year', evidenceStatus: 'corroborated'" in macro
assert "const PRODUCTION_POLICY_RATE_SERIES = ['policy-refinancing-rate', 'policy-rediscount-rate', 'policy-overnight-lending-rate'];" in macro
assert "const policyRate = productionState.indicatorIds.has('policy-refinancing-rate') ? ['policy-refinancing-rate'] : [];" in macro
assert "Current effective event only · no synthetic history is created." in macro
assert "independently corroborated SBV policy rates" in macro

loc=(ROOT/"assets/js/localization-dynamic.js").read_text(encoding="utf-8")
assert "'Policy Rediscount Rate': 'Lãi suất tái chiết khấu'" in loc
assert "'SBV Overnight Lending Facility Rate': 'Lãi suất cho vay qua đêm của NHNN'" in loc
assert "'Current effective event only · no synthetic history is created.'" in loc

html=(ROOT/"macro.html").read_text(encoding="utf-8")
assert "assets/js/macro.js?v=4.2K4" in html
assert "assets/js/localization-dynamic.js?v=4.2K4" in html

# Home does not need more cards, but it must count all persisted macro records.
home=(ROOT/"assets/js/home.js").read_text(encoding="utf-8")
assert "totalRecordCount: Array.isArray(payload?.data) ? payload.data.length : 0" in home

print("Phase 4.2K.4 frontend policy sync tests PASS")
