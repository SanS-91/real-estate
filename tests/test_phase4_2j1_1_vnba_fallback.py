from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
from collectors.vnba_customer_rates import parse_vnba_customer_rates,discover_vnba_customer_rates_url
FIX=ROOT/"tests/fixtures"
url=discover_vnba_customer_rates_url((FIX/"vnba_customer_rates_listing_sample.html").read_text(),"https://vnba.org.vn/en/hashtag/lending-interest-rates-29629")
assert "august-2026-23634" in url
rows=parse_vnba_customer_rates((FIX/"vnba_customer_rates_sample.html").read_text(),url,"2026-10-05T11:30:00+00:00")
by={x["indicator_id"]:x for x in rows}
assert len(rows)==5,rows
assert by["deposit-rate-vnd-6-12m-low"]["value"]==6.5 and by["deposit-rate-vnd-6-12m-high"]["value"]==8.0
assert by["lending-rate-vnd-average-low"]["value"]==8.4 and by["lending-rate-vnd-average-high"]["value"]==10.7
assert by["priority-short-term-lending-rate-vnd"]["value"]==3.9
assert all(x["source_id"]=="vnba" and x["evidence_status"]=="reported" and x["period"]=="2026-08" for x in rows)
live=json.loads((ROOT/"config/live_sources.json").read_text()); src=next(x for x in live["sources"] if x["key"]=="vnba-customer-rates"); assert src["canonical_eligible"] is False
pools=json.loads((ROOT/"config/source_pools.json").read_text()); pool=next(x for x in pools["pools"] if x["id"]=="customer-rates"); assert pool["preferred_source_ids"]==["sbv-vietnam"] and pool["fallback_source_ids"]==["vnba","vna-vietnamplus"] and pool["min_independent_sources_for_corroborated"]==2
prod=json.loads((ROOT/"config/production_promotion_policy.json").read_text()); assert all(i not in prod["allowed_indicators"] for i in pool["indicator_ids"])
print("Phase 4.2J.1.1 VNBA fallback discovery tests passed")
