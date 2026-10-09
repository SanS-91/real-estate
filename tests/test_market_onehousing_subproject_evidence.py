"""Verified nested OneHousing monthly price references never overwrite township ASP."""
import copy
import importlib.util
import json
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("gate",ROOT/"scripts/market_onehousing_subproject_gate.py")
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
data=json.loads((ROOT/"data/mock/market/alternative-subproject-monthly-evidence.json").read_text())
rows=data["data"]
projects={x["id"] for x in json.loads((ROOT/"data/mock/market/projects.json").read_text())["data"]}
sources={x["id"] for x in json.loads((ROOT/"data/mock/core/sources.json").read_text())["data"]}
assert data["record_count"]==2
assert not gate.validate(rows,projects,sources,date(2026,10,9))
assert {r["subproject_id"] for r in rows}=={"lumiere-boulevard","masteri-centre-point"}
assert {r["period"] for r in rows}=={"2026-09"}
for i in range(2):
    for field,bad in [
        ("project_id","the-global-city"),("source_id","rever-vn"),
        ("asset_type","landed"),("metric_type","project-average-asp"),
        ("subproject_name","Vinhomes Grand Park"),
        ("value_vnd_per_m2",300_000_000),
        ("range_high_vnd_per_m2",5_000_000),
        ("period","2026-10"),("review_date","2026-08-01"),
        ("source_url","https://not-onehousing.vn/prices")]:
        tampered=copy.deepcopy(rows)
        tampered[i][field]=bad
        assert gate.validate(tampered,projects,sources,date(2026,10,9)),(i,field)
    tampered=copy.deepcopy(rows);tampered[i]["evidence"]["metric"]="Đơn giá 100 triệu/m²"
    assert gate.validate(tampered,projects,sources,date(2026,10,9))
market=(ROOT/"assets/js/market.js").read_text()
store=(ROOT/"assets/js/data-store.js").read_text()
assert "getOneHousingSubprojectEvidence()" in market
assert "oneHousingSubprojectEvidence: payloadData(oneHousingSubprojectEvidence)" in market
assert "...data.oneHousingSubprojectEvidence" in market
assert "getOneHousingSubprojectEvidence:" in store
assert "projectIds.includes(item.project_id)" in market
assert "function alternativePriceCardsHTML" in market
assert "row.subproject_name ?" in market and "productNames[row.asset_type]" in market
assert "oneHousingSubprojectEvidence" not in market[market.index("function listingRangeChartData"):market.index("function priceLayerControls")]
assert json.loads((ROOT/"data/mock/market/listing-observations.json").read_text())["record_count"]==18
assert json.loads((ROOT/"data/mock/market/alternative-monthly-history.json").read_text())["record_count"]==1
assert json.loads((ROOT/"data/candidate/market/alternative-price-review-queue.json").read_text())["record_count"]==0
print("PASS: two source-dated subproject price references isolated from 12 parent project and price-history chart.")
