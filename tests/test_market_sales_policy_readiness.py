"""Marketing policy attribution, complete contractual payment PV gate and synthetic math."""
import importlib.util,json
from pathlib import Path
from datetime import date
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("scheme",ROOT/"scripts/build_market_sales_policy_readiness.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
raw=m.load(m.RAW)
projects=m.load(m.PROJECTS)
sources=m.load(m.SOURCES)
assert len(raw["data"])==raw["record_count"]==3
out=m.build(raw,projects,sources,date(2026,10,28))
assert len(out["watchlist"])==6
assert out["ready_for_fs_pv"]==0
assert out["current_approved_official_schemes"]==0
assert not out["source_refresh_is_price_refresh"]
assert all(x["customer_payment_pv_vnd"] is None and x["verified_net_selling_price_vnd"] is None
           and x["fs_comparison_ready"] is False for x in out["data"])
assert {x["project_id"] for x in out["data"]}=={"izumi-city","aqua-city"}
sec=next(x for x in out["data"] if x["source_role"].startswith("third-party"))
assert sec["source_id"]=="tapdoannamlong-secondary"
assert sec["published_terms"]["advertised_upfront_pct"]==60
assert sec["published_terms"]["guaranteed_post_handover_pct"]==35
assert sec["published_terms"]["retention_title_pct"]==5
assert sec["published_terms"]["max_months_after_handover"]==24
assert sec["fs_comparison_ready"] is False
assert "Incomplete" in sec["pv_block_reason"]
official=next(x for x in out["data"] if x["id"]=="izumi-canaria-launch-official-sep2026")
assert official["source_role"]=="developer-primary"
assert official["published_terms"]["launch_date"]=="2026-09-20"
assert official["published_terms"]["stated_price_vnd"] is None
historical=next(x for x in out["data"] if x["project_id"]=="aqua-city")
assert historical["status"]=="historical-unknown-validity"
assert historical["published_terms"]["historical_subsequent_instalment_pct"]==5
assert historical["published_terms"]["historical_bank_grace_months_min"]==24
# No synthetic "example" values are ever placed into the source dataset.
assert all("verified_net_price_vnd" not in x for x in raw["data"])
assert all(not x["verified_full_instalments"] for x in raw["data"])
# Explicitly synthetic test fixture only: net 100m VND, 50% at month 0 and month 12.
# With 12% annual discount, result is 50m + 50m/1.12 = 94,642,857 VND.
fixture={"status":"verified-current-contractual-policy","official_price_list_verified":True,
         "net_price_verified":True,"discount_stacking_verified":True,
         "verified_vat_basis":"VAT-inclusive-contract", "verified_contract":{"is_current":True},
         "source_publication_date":"2026-10-01","valid_from":"2026-10-01","valid_until":"2027-12-31",
         "verified_net_price_vnd":100_000_000,
         "verified_full_instalments":[{"due_date":"2026-10-28","pct_of_net_price":50,"due_basis":"contractual-exact-date"},
                                     {"due_date":"2027-10-28","pct_of_net_price":50,"due_basis":"contractual-exact-date"}]}
pv=m.calc_pv_if_complete(fixture,.12,date(2026,10,28))
assert pv==94642857,pv
bad=deepcopy(fixture);bad["verified_full_instalments"][1]["pct_of_net_price"]=45
assert m.calc_pv_if_complete(bad,.12,date(2026,10,28)) is None
bad=deepcopy(fixture);bad["verified_full_instalments"][1]["due_date"]=None
assert m.calc_pv_if_complete(bad,.12,date(2026,10,28)) is None
bad=deepcopy(fixture);bad["verified_contract"]["is_current"]=False
assert m.calc_pv_if_complete(bad,.12,date(2026,10,28)) is None
bad=deepcopy(fixture);bad["verified_vat_basis"]=None
assert m.calc_pv_if_complete(bad,.12,date(2026,10,28)) is None
# Synthetic first-party contractual scheme: only complete source + exact dates + explicit
# discount assumption may promote net price and customer PV. NEVER persisted in real data.
complete=deepcopy(raw["data"][0])
complete.update({"id":"synthetic-test-only-not-production",
                 "status":"verified-current-contractual-policy",
                 "source_publication_date":"2026-10-01",
                 "official_price_list_verified":True,"net_price_verified":True,
                 "discount_stacking_verified":True,"verified_net_price_vnd":100_000_000,
                 "verified_vat_basis":"VAT-inclusive-contract",
                 "verified_contract":{"is_current":True},
                 "valid_from":"2026-10-01","valid_until":"2027-12-31",
                 "comparison_discount_rate_annual":0.12,
                 "verified_full_instalments":deepcopy(fixture["verified_full_instalments"])})
ready=m.build({"record_count":1,"data":[complete]},projects,sources,date(2026,10,28))
assert ready["ready_for_fs_pv"]==1
assert ready["current_approved_official_schemes"]==1
assert ready["data"][0]["customer_payment_pv_vnd"]==94642857
assert ready["data"][0]["fs_comparison_ready"] is True
assert ready["data"][0]["verified_net_selling_price_vnd"]==100_000_000
assert next(r for r in ready["watchlist"] if r["project_id"]=="izumi-city")["pv_eligible_count"]==1
uncomplete=deepcopy(complete);uncomplete["comparison_discount_rate_annual"]=None
notready=m.build({"record_count":1,"data":[uncomplete]},projects,sources,date(2026,10,28))
assert notready["ready_for_fs_pv"]==0
assert notready["data"][0]["customer_payment_pv_vnd"] is None

bad=deepcopy(raw);bad["data"][0]["source_url"]="https://tapdoannamlong.com/official"
try:m.build(bad,projects,sources,date(2026,10,28))
except ValueError:pass
else:raise AssertionError("Spoofed official origin accepted")
print("PASS Phase 8B source attribution, policy readiness, no invented PV, synthetic annual-compound PV mathematics")
