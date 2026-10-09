from pathlib import Path
import argparse
import importlib.util
import json

ROOT=Path(__file__).resolve().parents[1]

spec=importlib.util.spec_from_file_location("assisted", ROOT/"scripts/listing_assisted_ingest.py")
assisted=importlib.util.module_from_spec(spec)
spec.loader.exec_module(assisted)

sources=assisted.listing_sources()
assert "batdongsan-com-vn" in sources
assert sources["batdongsan-com-vn"]["access_mode"]=="assisted-browser"
assert "cbre-vietnam" not in sources  # consultancy reports are not listing-asking sources

prod=json.loads((ROOT/"data/mock/market/listing-observations.json").read_text(encoding="utf-8"))
# Fixture captures originally compared against the 08 Oct baseline, not current history.
prod["data"]=[x for x in prod["data"] if x.get("observation_date")=="2026-10-08"]
base={x["project_id"]:x for x in prod["data"]}["mizuki-park"]

args=argparse.Namespace(
    source_id="batdongsan-com-vn",
    project_id="mizuki-park",
    source_url=base["source_url"],
    date="2026-10-09",
    source_data_as_of="2026-10-09",
    price_low_mn="58.0",
    price_high_mn="74.0",
    trend_pct="20.0",
    area_low_sqm="56",
    area_high_sqm="107",
    listing_count="270",
    views_7d="3600",
)
row=assisted.build_candidate(base,args)
assert row["asking_price_low_vnd_per_m2"]==58_000_000
assert row["asking_price_high_vnd_per_m2"]==74_000_000
assert row["asking_price_change_1y_pct"]==0.20
assert row["confidence"]=="assisted-reviewed-input"
assert row["provenance"]["capture_mode"]=="assisted-browser"
assert row["status"]=="candidate"

spec2=importlib.util.spec_from_file_location("pipeline", ROOT/"scripts/listing_snapshot_pipeline.py")
pipeline=importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(pipeline)
assert pipeline.validate([row])==[]
decision=pipeline.classify(prod["data"],[row])[0]
assert decision["status"]=="new-changed"

bad=dict(row)
bad["source_id"]="cbre-vietnam"
assert any("not registered for listing-asking" in x for x in pipeline.validate([bad]))

print("Phase 5.5E source diversification + assisted listing refresh tests PASS")
