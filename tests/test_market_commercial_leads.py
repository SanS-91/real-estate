"""Third-party zone starting prices and policy replacement must stay out of FS."""
import importlib.util,json
from pathlib import Path
from datetime import date
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("leads",ROOT/"scripts/build_market_commercial_leads.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=m.read(m.SRC);sources=m.read(m.SOURCES);projects=m.read(m.PROJECTS)
result=m.build(raw,sources,projects,date(2026,10,28))
assert result["source_price_leads"]==4
assert result["policy_changes_reported"]==2
assert result["verified_developer_price_rows"]==0
assert result["eligible_net_price_pv"]==0
assert result["no_automatic_promotion"] is True
assert {(r["zone"],r["starting_price_vnd"]) for r in result["prices"]} == {
    ("Zone 1",8550000000),("Zone 2",9180000000),("Zone 3",9520000000),
    (None,16400000000)}
assert all(r["price_status"]=="unverified-dealer-lead" and r["fs_eligible"] is False and
           r["payment_pv_vnd"] is None and r["project_asp_vnd_per_sqm"] is None and
           r["contract_net_price_vnd"] is None for r in result["prices"])
versions={r["reported_notice_id"]:r for r in result["policy_versions"]}
old=versions["TB143/2026/DNWF/TB"]
new=versions["TB153/2026/DNWF/TB"]
assert old["status"]=="reported-superseded"
assert old["successor_notice_id"]==new["reported_notice_id"]
assert old["reported_valid_until"]=="2026-10-04"
assert new["reported_valid_from"]=="2026-10-05"
assert new["reported_valid_until"]=="2026-12-31"
assert all(r["signed_notice_received"] is False and r["discounts_verified"] is False for r in versions.values())
def invalid(change,field="price"):
    p=deepcopy(raw)
    if field=="price":p["price_leads"][0].update(change)
    else:p["policy_events"][0].update(change)
    try:m.build(p,sources,projects,date(2026,10,28))
    except (ValueError,TypeError,KeyError):return
    raise AssertionError(f"Invalid broker evidence admitted: {change}")
invalid({"eligible_for_net_price":True})
invalid({"eligible_for_pv":True})
invalid({"individual_unit_code":"B1-01"})
invalid({"land_area_sqm":114})
invalid({"signed_original_price_sheet_verified":True})
invalid({"source_url":"https://not-a-dealer.example/izumi"})
invalid({"starting_asking_price_vnd":-1})
invalid({"reported_valid_until":"2026-12-31"},field="policy")
print("PASS dealer starting-price candidates, issuer supersession and zero unsupported FS pricing/PV")
