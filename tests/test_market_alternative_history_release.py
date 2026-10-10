"""Round 4D: strict manual approval and source-isolated monthly history."""
from __future__ import annotations
import copy, importlib.util, json
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location("release", ROOT/"scripts/market_alternative_history_release.py")
rel=importlib.util.module_from_spec(sp); sp.loader.exec_module(rel)

history=json.loads((ROOT/"data/mock/market/alternative-monthly-history.json").read_text())["data"]
queue=json.loads((ROOT/"data/candidate/market/alternative-price-review-queue.json").read_text())["data"]
approvals=json.loads((ROOT/"config/market-alternative-reviewed-approvals.json").read_text())["data"]
assert len(history)==1 and history[0]["period"]=="2026-10"
assert not approvals
assert all(row.get("candidate_only") is True and row.get("review_required") is True for row in queue)
assert all(row.get("period") != history[0]["period"] or row.get("project_id") != history[0]["project_id"] or row.get("subproject_name") for row in queue)
assert not rel.base_issues(history)
assert rel.eligible_monthly(history[0]) and rel.quoted_metrics_match(history[0])
assert rel.evaluate(history,queue,approvals,date(2026,10,9)) == ([],[],[])

def candidate(period, val="55.10", low="38.40", high="250.25"):
    base=copy.deepcopy(history[0])
    base.update(id="candidate-onehousing-vinhomes-grand-park-apartment-"+period,
                baseline_record_id=rel.BASELINE_ID,source_record_id=None,series_key=None,
                review_status=None,review_date=None,candidate_only=True,review_required=True,
                period=period,value_vnd_per_m2=rel.vnd(val),
                range_low_vnd_per_m2=rel.vnd(low),range_high_vnd_per_m2=rel.vnd(high),
                evidence={"period":"Căn hộ chung cư dự án Vinhomes Grand Park tháng "+
                           str(int(period[5:]))+"/"+period[:4],
                          "metric":"Đơn giá phổ biến | "+val+" triệu/m²",
                          "range":"Khoảng giá: "+low+" - "+high+" triệu"})
    return base

def approval(row, review_day="2026-11-20"):
    return {"candidate_id":row["id"],"review_date":review_day,
            "checked_source_evidence":True,
            "review_note":"Verified public OneHousing apartment modal asking price and source period for this specific project; not official ASP."}

next_month=candidate("2026-11")
app=approval(next_month)
ready,decisions,issues=rel.evaluate(history,[next_month],[app],date(2026,11,20))
assert not issues and len(ready)==1
assert decisions[0]["status"]=="ready"
assert ready[0]["period"]=="2026-11" and ready[0]["review_status"]=="reviewed-release"
assert ready[0]["series_key"]==rel.SERIES_KEY
assert ready[0]["review_date"]=="2026-11-20"
assert "candidate_only" not in ready[0] and "average_asp" not in ready[0]
assert (ready[0]["value_vnd_per_m2"],ready[0]["range_high_vnd_per_m2"]) == (55_100_000,250_250_000)
already,decisions,issues=rel.evaluate(history+ready,[next_month],[app],date(2026,11,20))
assert not already and decisions[0]["status"]=="already-published" and not issues

def blocked(row, a, token):
    adds,desc,issues=rel.evaluate(history,[row],[a],date(2026,11,20))
    assert not adds and token in desc[0]["issues"],(token,desc,issues)
bad=copy.deepcopy(next_month);bad["source_id"]="rever-vn"
blocked(bad,app,"candidate-source-price-scope-mismatch")
bad=copy.deepcopy(next_month);bad["asset_type"]="villa-townhouse"
blocked(bad,app,"candidate-source-price-scope-mismatch")
bad=copy.deepcopy(next_month);bad["value_vnd_per_m2"]=1_000_000_000
blocked(bad,app,"candidate-source-price-scope-mismatch")
bad=copy.deepcopy(next_month);bad["period"]="2026-12"
blocked(bad,app,"candidate-source-price-scope-mismatch")
bad=copy.deepcopy(next_month);bad["source_url"]="https://other-source.example/"
blocked(bad,app,"candidate-source-price-scope-mismatch")
bad=copy.deepcopy(next_month);bad["review_required"]=False
blocked(bad,app,"candidate-not-review-pending")
bad=copy.deepcopy(next_month);bad["baseline_record_id"]="rever-listing"
blocked(bad,app,"candidate-does-not-belong-to-original-series")
bad=copy.deepcopy(next_month);bad["review_date"]="2026-11-20"
blocked(bad,app,"candidate-already-has-review-date")
badapproval=copy.deepcopy(app);badapproval["checked_source_evidence"]=False
blocked(next_month,badapproval,"publisher-evidence-not-approved")
badapproval=copy.deepcopy(app);badapproval["review_date"]="2026-11-02";badapproval["review_note"]="not reviewed"
blocked(next_month,badapproval,"insufficient-review-note")
badapproval=copy.deepcopy(app);badapproval["review_date"]="2026-12-25"
blocked(next_month,badapproval,"approval-from-future")
missing,desc,issues=rel.evaluate(history,[],[app],date(2026,11,20))
assert desc[0]["status"]=="blocked" and "candidate-not-in-immutable-review-queue" in desc[0]["issues"]
same=copy.deepcopy(next_month)
same["period"]="2026-10"
same["evidence"]["period"]="Căn hộ chung cư dự án Vinhomes Grand Park tháng 10/2026"
same["id"]="candidate-onehousing-vinhomes-grand-park-apartment-2026-10"
same["value_vnd_per_m2"]=history[0]["value_vnd_per_m2"]
same["range_low_vnd_per_m2"]=history[0]["range_low_vnd_per_m2"]
same["range_high_vnd_per_m2"]=history[0]["range_high_vnd_per_m2"]
same["evidence"]=copy.deepcopy(history[0]["evidence"])
already,decisions,_=rel.evaluate(history,[same],[approval(same)],date(2026,11,20))
assert not already and decisions[0]["status"]=="already-published"
same["value_vnd_per_m2"]=56_000_000
_,decisions,_=rel.evaluate(history,[same],[approval(same)],date(2026,11,20))
assert "conflicting-existing-period" in decisions[0]["issues"]
assert rel.base_issues(history+[history[0]])
original=json.loads((ROOT/"data/mock/market/listing-observations.json").read_text())
assert original["record_count"]>=18
print("PASS: 1 real OneHousing monthly baseline; preview empty; forged dates, prices, sources and approvals rejected.")
