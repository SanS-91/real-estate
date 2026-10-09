"""Round 4 alternative source data: strict evidence/date/type isolation."""
import copy
import importlib.util
import json
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("gate",ROOT/"scripts/market_alternative_source_gate.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
payload=json.loads((ROOT/"data/mock/market/alternative-price-evidence.json").read_text(encoding="utf-8"))
rows=payload["data"]
projects={x["id"] for x in json.loads((ROOT/"data/mock/market/projects.json").read_text(encoding="utf-8"))["data"]}
sources={x["id"] for x in json.loads((ROOT/"data/mock/core/sources.json").read_text(encoding="utf-8"))["data"]}
assert len(rows)==payload["record_count"]==5
assert {r["source_id"] for r in rows}=={"onehousing-vn","rever-vn"}
assert {r["project_id"] for r in rows}=={"vinhomes-grand-park","the-global-city","the-privia","lumiere-riverside"}
assert not gate.validate(rows,sources,projects,date(2026,10,9))
for index,field,bad in [(0,"value_vnd_per_m2",111),(0,"range_high_vnd_per_m2",900_000_000),(1,"period","2026-10-09"),(2,"source_id","batdongsan-com-vn"),(3,"project_id","izumi-city"),(0,"review_date","2026-11-01")]:
    corrupt=copy.deepcopy(rows)
    corrupt[index][field]=bad
    assert gate.validate(corrupt,sources,projects,date(2026,10,9)),(index,field)
existing=json.loads((ROOT/"data/mock/market/listing-observations.json").read_text(encoding="utf-8"))
scope=json.loads((ROOT/"data/mock/market/listing-scope-evidence.json").read_text(encoding="utf-8"))
assert existing["record_count"]==18 and scope["record_count"]==4
assert all(r["metric_type"]!="project-asp" for r in rows)
assert not any(r.get("listing_asking_series",False) for r in rows)
assert all(r["period"] != r["review_date"] for r in rows if r["period_type"]=="month")
print("PASS: 5 alternative observations; tamper detection; 18 existing snapshots and 4 scope references unchanged.")
