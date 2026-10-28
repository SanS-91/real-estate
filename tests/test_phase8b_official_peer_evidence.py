"""Protect first-party project facts from becoming fake sales, ASP, or actual handovers."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
read=lambda p: json.loads((ROOT/p).read_text(encoding="utf-8"))
payload=read("data/mock/market/developer-project-evidence.json")
project_ids={p["id"] for p in read("data/mock/market/projects.json")["data"]}
sources={p["id"] for p in read("data/mock/core/sources.json")["data"]}
rows=payload["data"]
assert payload["record_count"] == len(rows) == 2
assert {x["project_id"] for x in rows} == {"aqua-city", "springville"}
assert all(x["project_id"] in project_ids and x["source_id"] in sources for x in rows)
assert all(x["source_url"].startswith("https://") and x.get("review_date") for x in rows)
assert all(not any(key in x for key in ("average_asp","absorption_rate","sales_units","realized_handover_units")) for x in rows)
aqua=next(row for row in rows if row["project_id"]=="aqua-city")
assert aqua["category"]=="developer-forward-plan"
assert aqua["status"]=="company-stated-forward-looking"
assert aqua["source_publication_date"]=="2026-10-16"
assert aqua["milestone"]["date"]=="2026-10-31"
assert aqua["milestone"]["is_future_at_review"] is True
facts={x["metric_id"]:x for x in aqua["facts"]}
assert facts["planned-construction-units-lower-bound"]["value"]==1000
assert facts["planned-handover-units-lower-bound"]["value"]==500
assert all(f["comparison"]=="greater-than" and f["not_actual"] for f in aqua["facts"])
spring=next(row for row in rows if row["project_id"]=="springville")
assert spring["source_publication_date"] is None
assert spring["price_publication_status"]=="not-published-on-developer-page"
assert {"commercial-townhouse","townhouse","apartment"} <= set(spring["product_types"])
assert spring["facts"][0]["value"]==18.2
assert spring["facts"][1]["value"]==66.7
assert spring["facts"][2]["value"]==183.1
js=(ROOT/"assets/js/market.js").read_text(encoding="utf-8")
store=(ROOT/"assets/js/data-store.js").read_text(encoding="utf-8")
maintenance=(ROOT/"assets/js/maintenance.js").read_text(encoding="utf-8")
html=(ROOT/"maintenance.html").read_text(encoding="utf-8")
assert "DataStore.getDeveloperProjectEvidence()" in js
assert "function developerFirstPartyEvidenceHTML(project)" in js
assert "developerFirstPartyEvidenceHTML(project)" in js
assert "getDeveloperProjectEvidence" in store
assert "Không phải kết quả thực tế" in js or "không phải kết quả thực tế" in js
assert "renderPeerAlternativeWatch" in maintenance
assert "data/state/market-peer-alternative-health.json" in maintenance
assert 'data-peer-alternative-watch' in html
assert "source_prices_updated !== false" in maintenance
print("PASS: first-party Aqua plan/Springville product facts stay source-attributed, not ASP or realized sales")
