"""Alternative source watch only: identity, access, content change and no price promotion."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("alternative",ROOT/"scripts/market_peer_alternative_watch.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cfg=json.loads((ROOT/"config/market-peer-alternative-targets.json").read_text(encoding="utf-8"))
now=datetime(2026,10,28,9,0,tzinfo=timezone.utc)
pages={
  "aqua-city":"Aqua City product news. "+("The developer plans 2026 construction and handover. "*12),
  "springville":"Springville integrated township. Giá từ VND TBU. "+("Townhouse apartment and retail. "*12),
  "elyse-island":"Elyse Island island township. "+("Official project description. "*12),
  "kita-airport-city":"KITA Airport City urban district. "+("Product and phase information. "*12)
}
def fetch(url):
    project=next(x["project_id"] for x in cfg["targets"] if x["url"]==url)
    return SimpleNamespace(status_code=200,url=url,text="<html><main>"+pages[project]+"</main></html>")

a=mod.build(cfg,{},now,fetch)
assert a["targets_checked"]==5
assert a["target_coverage_projects"]==4
assert a["status_counts"]["baseline-created"]==5
assert a["source_prices_updated"] is False and a["price_candidates_promoted"]==0
assert not any(row["review_required"] for row in a["targets"])
spring=next(row for row in a["targets"] if row["target_id"]=="springville-gamuda")
assert spring["price_publication_status"]=="official-price-not-disclosed-vnd-tbu"
b=mod.build(cfg,a,now+timedelta(hours=4),fetch)
assert b["status_counts"]["unchanged"]==5
pages["springville"] += " Latest source webpage updated."
c=mod.build(cfg,b,now+timedelta(days=1),fetch)
assert c["status_counts"]["content-changed-review"]==2
assert c["price_candidates_promoted"]==0 and c["source_prices_updated"] is False

def blocked(url):
    return SimpleNamespace(status_code=403,url=url,text="")
d=mod.build(cfg,c,now+timedelta(days=2),blocked)
assert d["status_counts"]["blocked"]==5
assert all(x["last_valid_fingerprint"] for x in d["targets"])
assert all(x["new_prices_verified"]==0 for x in d["targets"])
assert mod.valid_target({**cfg["targets"][0],"url":"https://evil.example/aqua-city"}) is False
assert mod.valid_target({**cfg["targets"][0],"price_metric_allowed":True}) is False
assert mod.observe(cfg["targets"][0],None,now,lambda u:SimpleNamespace(
  status_code=200,url=u,text="<html><body>Unrelated content only "*10+"</body></html>")
)["status"]=="identity-unverified"
print("PASS: alternative source watch baseline, change detection, block recovery, strict identity, zero price promotion")
