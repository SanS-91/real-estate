"""Product benchmark: sourced units, strict land-vs-apartment basis, no FS promotion."""
import importlib.util
import json
from pathlib import Path
from datetime import date
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("product_benchmark",ROOT/"scripts/build_product_comparables.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
raw=mod.read(mod.RAW)
projects=mod.read(mod.PROJECTS)
sources=mod.read(mod.SOURCES)
result=mod.build(raw,projects,sources,date(2026,10,28))
assert len(raw["records"])>=6
assert result["record_count"]==len(raw["records"])
assert result["verified_live_count"]==0
assert result["official_payment_schedules"]==0
assert {"dong-nai","can-tho","hcmc"} <= {r["region_id"] for r in result["data"]}
assert len(result["watchlist_coverage"])==6
assert all(r["is_verified_live_offer"] is False and r["fs_asp_eligible"] is False
           and r["fs_absorption_eligible"] is False for r in result["data"])
assert all(r["discount_to_pv_vnd"] is None and not r["verified_payment_milestones"]
           for r in result["data"])
assert all(r["market_layer"]=="historical-individual-asking-only" for r in result["data"])
assert all(r["source_id"]=="cafeland-listings" and r["source_url"].startswith("https://nhadat.cafeland.vn/")
           for r in result["data"])
assert all("land-area-reported-by-publisher"==r["price_area_basis"] and r["land_area_sqm"]
           for r in result["data"] if r["product_type"]!="apartment")
nine=next(r for r in result["data"] if r["project_id"]=="the-9-stellars")
assert nine["land_area_sqm"] is None
assert nine["advertised_apartment_area_sqm"]==100
assert nine["construction_floor_area_sqm"] is None
assert nine["source_listed_date"]=="2025-01-05"
aqua=[r for r in result["data"] if r["project_id"]=="aqua-city"]
assert len(aqua)>=2
assert any(r["phase_name"]=="River Park 2" for r in aqua)
assert all(r["listing_status"]=="expired-at-review" for r in aqua if r["id"] in (
  "cafeland-aqua-river-park-2-corner-20260721", "cafeland-aqua-river-villa-20260717"))
assert any(r["upfront_claim_vnd"]==3880000000 and r["payment_scheme_status"]=="not-officially-verified"
           for r in aqua)
kita=next(r for r in result["data"] if r["project_id"]=="kita-airport-city")
assert kita["product_type"]=="landlot" and kita["land_area_sqm"]==102.15
assert kita["price_vnd_per_unit"]==1700000000
assert kita["unit_price_vnd_per_sqm"]==16600000
assert kita["listing_status"]=="unverified-current"
assert sum(r["historical_individual_offers"] for r in result["watchlist_coverage"])>=4
assert sum(r["live_offers_verified"] for r in result["watchlist_coverage"])==0
assert next(r for r in result["watchlist_coverage"] if r["project_id"]=="springville")["historical_individual_offers"]>=0
assert mod.build(raw,projects,sources,date(2026,10,28))["build_revision"]==result["build_revision"]
# Invalid assumptions must fail closed.
def reject(update):
    b=deepcopy(raw);b["records"][0].update(update)
    try:mod.build(b,projects,sources,date(2026,10,28))
    except (ValueError,KeyError):return
    raise AssertionError(f"Invalid data accepted: {update}")
reject({"source_url":"https://other-domain.example/ad"})
reject({"land_area_sqm":None})
reject({"listed_unit_area_sqm":250})
reject({"total_asking_vnd":1})
reject({"verified_developer_payment":True})
reject({"payment_schedule":[{"date":"2026-12-01","pct":1}]})
reject({"reviewed_date":"2026-11-01"})
reject({"listing_status":"active-verified"})
print("PASS Phase 8B: source-backed individual-product records scale without synthetic prices or payments")
