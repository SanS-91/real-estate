"""Unattended 4G release must be safe, repeatable, and preserve source identity."""
from __future__ import annotations
import copy, json, sys
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import market_subproject_monthly_release as release
import market_subproject_candidate_recheck as verifier
import market_alternative_auto_probe as collector

def read(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
baselines=read("data/mock/market/alternative-subproject-monthly-evidence.json")["data"]
history=read("data/mock/market/alternative-subproject-monthly-history.json")["data"]
fixture_history=[r for r in history if r["review_status"]=="source-indexed-baseline"]
queue=read("data/candidate/market/alternative-price-review-queue.json")["data"]
assert len(fixture_history)==2
lumiere=next(x for x in queue if x.get("subproject_name")=="Lumière Boulevard")
assert lumiere["period"]=="2026-10"
assert not release.validate_history(history,baselines)

signature=verifier.content_signature(lumiere)
def check(run_id,t,status="matched-source-period-and-metric",price_status=200):
    return dict(run_id=str(run_id),checked_at=t,status=status,
                source_http_status=price_status,source_final_host="onehousing.vn",
                candidate_signature=signature)
def record(checks):
    return dict(candidate_id=lumiere["id"],source_url=lumiere["source_url"],
                period=lumiere["period"],subproject_name=lumiere["subproject_name"],
                candidate_signature=signature,checks=checks)
today=date(2026,10,9)
c1=check(101,"2026-10-09T02:00:00+00:00")
c2=check(102,"2026-10-09T05:00:00+00:00")
rec=record([c1,c2])
auto,status=release.build_auto_approvals(fixture_history,baselines,queue,[rec],[],today)
assert len(auto)==1,status
assert auto[0]["verification_run_ids"]==["101","102"]
rows,decisions,issues=release.evaluate(fixture_history,baselines,queue,[rec],auto,today)
assert not issues and not decisions[0]["issues"] and len(rows)==1
row=rows[0]
row["review_status"]="automated-source-verified"
row["verification_mode"]="two-independent-live-publisher-checks"
row["verified_at"]="2026-10-09"
assert not release.validate_history(fixture_history+[row],baselines)

# Reruns never append a second October observation.
repeated,status=release.build_auto_approvals(fixture_history+[row],baselines,queue,[rec],[],today)
assert not repeated and status[0]["status"]=="already-in-historical-series"

# One successful capture is insufficient.
auto,status=release.build_auto_approvals(fixture_history,baselines,queue,[record([c1])],[],today)
assert not auto and status[0]["status"]=="waiting-for-two-source-checks"

# Same workflow run cannot masquerade as two source rechecks.
cdup=check(101,"2026-10-09T05:00:00+00:00")
auto,status=release.build_auto_approvals(fixture_history,baselines,queue,[record([c1,cdup])],[],today)
assert not auto and status[0]["status"]=="source-proof-incomplete"

# Checks must be spaced at least one hour.
cshort=check(102,"2026-10-09T02:30:00+00:00")
auto,status=release.build_auto_approvals(fixture_history,baselines,queue,[record([c1,cshort])],[],today)
assert not auto

# Any newer failed source response blocks automatic release.
failed=check(102,"2026-10-09T05:00:00+00:00","source-revised-same-period")
auto,status=release.build_auto_approvals(fixture_history,baselines,queue,[record([c1,failed])],[],today)
assert not auto

# Content signature drift and HTTP 403 are not approved.
modified=record([c1,c2]);modified["candidate_signature"]="broken"
auto,status=release.build_auto_approvals(fixture_history,baselines,queue,[modified],[],today)
assert not auto
denied=check(102,"2026-10-09T05:00:00+00:00","blocked",403)
auto,status=release.build_auto_approvals(fixture_history,baselines,queue,[record([c1,denied])],[],today)
assert not auto

# A >30% price jump needs review instead of auto-release.
large=copy.deepcopy(lumiere)
large["value_vnd_per_m2"]=int(large["value_vnd_per_m2"]*1.6)
large["range_high_vnd_per_m2"]=int(large["range_high_vnd_per_m2"]*1.8)
large["evidence"]["metric"]="117.984 triệu/m²"
large["evidence"]["range"]="Khoảng giá: 57 - 180.342 triệu"
# The quote remains exact and valid; safety cap must be the reason.
assert release.quote_matches(large)
auto,status=release.build_auto_approvals(fixture_history,baselines,[large],[],[],today)
assert not auto and status[0]["status"]=="price-jump-needs-human-review"

# Same publisher canonical mirror path is allowed; changing property ID is not.
masteri=next(t for t in read("config/market-alternative-auto-targets.json")["targets"]
             if t["target_id"]=="onehousing-masteri-centre-point-apartment")
assert masteri["fallback_urls"]==[
 "https://onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Masteri-Centre-Point.53"]
assert collector.allowed_target({**masteri,"url":masteri["fallback_urls"][0]})
assert collector.onehousing_source_diagnostics(
 "Căn hộ chung cư dự án Masteri Centre Point tháng 9/2026 Đơn giá phổ biến 70.9 triệu/m²",
 "Masteri Centre Point")["publisher_project_header"]
assert "getOneHousingSubprojectHistory" in (ROOT/"assets/js/data-store.js").read_text()
market=(ROOT/"assets/js/market.js").read_text()
assert "automated-source-verified" in market
assert "published.get(item.subproject_name) || item" in market
assert "getOneHousingSubprojectHistory()" in market
assert "market-price-references" in market
assert read("data/mock/market/listing-observations.json")["record_count"]==18
print("PASS: scheduled auto-verified months require two >1h source checks; avoid 403, stale, outlier or replay; price reference uses latest valid release.")
