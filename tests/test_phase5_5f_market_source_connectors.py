from pathlib import Path
import importlib.util, json

ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/"config/market-automation-targets.json").read_text(encoding="utf-8"))
ids={x["target_id"] for x in cfg["targets"]}
assert "cbre-hcmc-q2-2026" in ids
assert "nam-long-news" in ids
assert all(x.get("url","").startswith("https://") for x in cfg["targets"])

spec=importlib.util.spec_from_file_location("connector",ROOT/"scripts/market_source_connector.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

html="<html><head><title>Market Q2 2026</title><meta name='description' content='Residential market update'></head><body>Published 2026-08-12</body></html>"
m=mod.page_meta(html)
assert m["title"]=="Market Q2 2026"
assert m["description"]=="Residential market update"
assert "2026-08-12" in m["date_mentions"]

print("Phase 5.5F market source connector tests PASS")
