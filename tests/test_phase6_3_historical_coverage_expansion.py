from pathlib import Path
import importlib.util, json

ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/"config/market-historical-backfill.json").read_text(encoding="utf-8"))
prod=json.loads((ROOT/"data/mock/market/observations.json").read_text(encoding="utf-8"))["data"]
sources={x["id"] for x in json.loads((ROOT/"data/mock/core/sources.json").read_text(encoding="utf-8"))["data"]}

assert len(cfg["records"])==5
assert len({x["id"] for x in cfg["records"]})==5
assert all(x["source_id"] in sources for x in cfg["records"])
assert all(x["source_url"].startswith("https://") for x in cfg["records"])

by_id={x["id"]:x for x in cfg["records"]}
assert by_id["obs-hcmc-apartment-2025-q3-cbre"]["new_supply"]==2549
assert by_id["obs-hcmc-landed-2025-q3-cbre"]["new_supply"]==220
assert by_id["obs-hcmc-landed-2025-q4-cbre"]["new_supply"]==4569
assert by_id["obs-hcmc-landed-2026-q1-cbre"]["new_supply"]==87
assert by_id["obs-hcmc-apartment-2026-q1-cushman"]["new_supply"]==1200
assert by_id["obs-hcmc-apartment-2026-q1-cushman"]["absorption_rate"]==0.25
assert by_id["obs-hcmc-apartment-2026-q1-cushman"]["metric_qualifiers"]["new_supply"]=="approx"
assert by_id["obs-hcmc-apartment-2026-q1-cushman"]["metric_qualifiers"]["absorption_rate"]=="approx"

# Historical backfill plus current production must create four-quarter CBRE
# series for both apartment and landed without blending sources.
combined=prod+cfg["records"]
def periods(segment,source):
    return sorted({
      x["period"] for x in combined
      if x.get("scope_type")=="region-segment"
      and x.get("region_ids")==["hcmc"]
      and x.get("segment_ids")==[segment]
      and x.get("source_id")==source
    })
assert periods("apartment","cbre-vietnam-market")==["2025-Q3","2025-Q4","2026-Q1","2026-Q2"]
assert periods("landed","cbre-vietnam-market")==["2025-Q3","2025-Q4","2026-Q1","2026-Q2"]
assert periods("apartment","cushman-wakefield-vietnam-market")==["2026-Q1","2026-Q2"]

spec=importlib.util.spec_from_file_location("coverage",ROOT/"scripts/build_history_coverage.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
coverage_cfg=json.loads((ROOT/"config/history-coverage.json").read_text(encoding="utf-8"))
market=mod.market_report(coverage_cfg,combined)
cbre=[
  x for x in market["items"]
  if x["source_id"]=="cbre-vietnam-market"
  and x["scope_type"]=="region-segment"
]
assert len(cbre)==2
assert all(x["trend_ready"] for x in cbre)

listing_rows=json.loads((ROOT/"data/mock/market/listing-observations.json").read_text(encoding="utf-8"))["data"]
listing=mod.listing_report(coverage_cfg,listing_rows)
assert listing["series_count"]==12
assert listing["trend_ready_series"]==0
assert all(1<=x["snapshot_count"]<=2 for x in listing["items"])
assert sum(x["snapshot_count"]==2 for x in listing["items"]) in (0,4)

legal_rows=json.loads((ROOT/"data/mock/legal/documents.json").read_text(encoding="utf-8"))["data"]
legal=mod.legal_report(coverage_cfg,legal_rows)
assert legal["history_ready"] is True
assert legal["year_count"]>=4

infra_rows=json.loads((ROOT/"data/mock/infrastructure/schedules.json").read_text(encoding="utf-8"))["data"]
infra=mod.infrastructure_report(coverage_cfg,infra_rows)
assert infra["history_ready_series"]>=3

print("Phase 6.3 historical coverage expansion tests PASS")


roadmap=json.loads((ROOT/"config/master-roadmap.json").read_text(encoding="utf-8"))
phase6=next(x for x in roadmap["master_phases"] if x["id"]=="6")
seq={x["work_package"]:x for x in roadmap["next_sequence"]}
if seq["6.3"].get("status")=="complete":
    prod_keys={
      (x.get("scope_type"),tuple(x.get("region_ids") or []),tuple(x.get("segment_ids") or []),x.get("period"),x.get("source_id"))
      for x in prod
    }
    for row in cfg["records"]:
        key=(row.get("scope_type"),tuple(row.get("region_ids") or []),tuple(row.get("segment_ids") or []),row.get("period"),row.get("source_id"))
        assert key in prod_keys
    assert phase6["status"]=="complete"
