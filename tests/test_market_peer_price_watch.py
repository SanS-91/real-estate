"""Price peer watch only monitors source availability; cannot invent price updates."""
import importlib.util
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("peerwatch",ROOT/"scripts/market_peer_price_watch.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

evidence=json.loads((ROOT/"data/mock/market/listing-scope-evidence.json").read_text(encoding="utf-8"))["data"]
ids={row["project_id"] for row in evidence}
assert {"izumi-city","aqua-city","springville","kita-airport-city","elyse-island"} <= ids

def ok(url):
    return SimpleNamespace(status_code=200,url=url)

result=mod.build(today=date(2026,10,28),fetcher=ok)
rows={row["project_id"]:row for row in result["projects"]}
assert result["counts"]["targets"]==5
assert result["source_verified_new_prices"]==0
assert result["production_prices_written"] is False
assert result["counts"]["historical_only"]==1
assert rows["springville"]["price_evidence"]=="historical-only"
assert rows["springville"]["price_caution"]=="historic-only"
assert rows["aqua-city"]["source_product_scope"]=="landed-only"
assert rows["kita-airport-city"]["source_product_scope"]=="landlot-only"
assert rows["elyse-island"]["price_caution"]=="source-activity-old"
assert rows["aqua-city"]["publisher_access"]=="reachable-unverified-price"
assert all(row["data_published_from_this_check"] is False for row in rows.values())
assert all("asking_price" not in row for row in rows.values()), "Report must not contain unverified extracted prices"

def blocked(url):
    return SimpleNamespace(status_code=403,url=url)

blocked_report=mod.build(today=date(2026,10,28),fetcher=blocked)
assert blocked_report["counts"]["blocked_sources"]==5
assert all(row["publisher_access"]=="blocked" for row in blocked_report["projects"])
assert mod.access("https://example.org/invalid",fetcher=ok)["state"]=="invalid-source-url"
print("PASS: peer price watch is source-only, age-aware, blocked-safe and price-immutable")
