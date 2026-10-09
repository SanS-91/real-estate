"""4F: exact source-month rechecks and subproject-only, review-gated releases."""
import copy
from datetime import date
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import market_alternative_auto_probe as probe
import market_subproject_candidate_recheck as verification
import market_subproject_monthly_release as release

load=lambda path:json.loads((ROOT/path).read_text(encoding="utf-8"))
baseline=load("data/mock/market/alternative-subproject-monthly-evidence.json")["data"]
history=load("data/mock/market/alternative-subproject-monthly-history.json")["data"]
queue=load("data/candidate/market/alternative-price-review-queue.json")["data"]
approvals=load("config/market-subproject-reviewed-approvals.json")["data"]
targets=load("config/market-alternative-auto-targets.json")["targets"]
assert len(baseline)==len(history)==2 and not approvals
assert len(queue)>=1
assert not release.validate_history(history,baseline)
assert {row["review_status"] for row in history}=={"source-indexed-baseline"}
assert {row["period"] for row in history}=={"2026-09"}
assert all(release.quote_matches(row) for row in history)
assert all(release.quote_matches(row) for row in baseline)
lumiere=next(r for r in queue if r.get("subproject_name")=="Lumière Boulevard")
base=next(r for r in baseline if r["subproject_name"]=="Lumière Boulevard")
target=next(r for r in targets if r.get("subproject_name")=="Lumière Boulevard")
assert lumiere["period"]=="2026-10"
assert lumiere["value_vnd_per_m2"]==73_740_000
assert release.candidate_in_series(lumiere,base)
assert release.quote_matches(lumiere)
assert release.evaluate(history,baseline,queue,[],approvals,date(2026,10,9)) == ([],[],[])

def fixture(name,month,modal="73.74",low="57",high="100.19"):
    return f"""<!doctype html><html><body><h1>{name}</h1>
    <p>Căn hộ chung cư dự án {name} tháng {month}/2026</p>
    <div>Biến động giá & giá nhà chung cư theo tháng; Dữ liệu của đúng phân khu</div>
    <h2>Giá phổ biến</h2><div>4.5 tỷ</div>
    <section>Đơn giá phổ biến Mức giá/ mét vuông xuất hiện nhiều nhất trong khoảng giá
    {modal} triệu/m² 0% Khoảng giá: {low} - {high} triệu
    Giá thuê phổ biến ~20 triệu/tháng</section></body></html>"""

today=date(2026,10,9)
good=fixture("Lumière Boulevard",10)
state,diag=verification.evaluate_html(lumiere,target,good,today)
assert state=="matched-source-period-and-metric",diag
assert diag["source_months"]==["2026-10"] and diag["source_project_header"]
assert diag["modal_section_present"] and diag["price_metric_token_present"]
state,_=verification.evaluate_html(lumiere,target,fixture("Lumière Boulevard",9),today)
assert state=="publisher-older-period"
state,_=verification.evaluate_html(lumiere,target,fixture("Lumière Boulevard",10,modal="79.99"),today)
assert state=="source-revised-same-period"
state,_=verification.evaluate_html(lumiere,target,fixture("Masteri Centre Point",10),today)
assert state=="publisher-metric-unverifiable"
state,diag=verification.evaluate_html(lumiere,target,"<html><body>Đăng nhập để xem giá</body></html>",today)
assert state=="publisher-metric-unverifiable" and diag["login_wall_visible"]

def fake_fetch(item,session):
    return {"status":"reachable","http_status":200,"final_host":"onehousing.vn"},good
empty={"schema_version":1,"data":[]}
check_time_1="2026-10-09T02:00:00+00:00"
check_time_2="2026-10-09T04:00:00+00:00"
s1,rep=verification.run_once(queue,targets,empty,today,"123451",check_time_1,fetcher=fake_fetch)
assert s1["record_count"]>=1 and rep["checked_candidates"]>=1
assert rep["production_prices_updated"] is False
v1=next(r for r in s1["data"] if r["candidate_id"]==lumiere["id"])
assert verification.current_verified(v1)=={
    "matching_run_count":1,"latest_source_status":"matched-source-period-and-metric","latest_matches":True}
s2,rep=verification.run_once(queue,targets,s1,today,"123452",check_time_2,fetcher=fake_fetch)
v2=next(r for r in s2["data"] if r["candidate_id"]==lumiere["id"])
assert verification.current_verified(v2)["matching_run_count"]==2
assert verification.content_signature(lumiere)==v2["candidate_signature"]
repeat,_=verification.run_once(queue,targets,s2,today,"123452","2026-10-09T04:05:00+00:00",fetcher=fake_fetch)
assert len(next(r for r in repeat["data"] if r["candidate_id"]==lumiere["id"])["checks"])==2
approval={"candidate_id":lumiere["id"],
          "review_date":"2026-10-09",
          "review_note":"Independently audited exact source-authored October month, subproject apartment scope, quoted modal and asking range from two GitHub-hosted publisher captures.",
          "checked_source_evidence":True,
          "verification_run_ids":["123451","123452"]}
assert not release.verification_proofs(v2,lumiere,approval)
ready,decisions,issues=release.evaluate(history,baseline,queue,s2["data"],[approval],today)
assert not issues and len(ready)==1 and decisions[0]["status"]=="ready"
assert ready[0]["subproject_name"]=="Lumière Boulevard"
assert ready[0]["series_key"]=="onehousing-lumiere-boulevard-apartment-popular-asking"
assert ready[0]["period"]=="2026-10" and ready[0]["value_vnd_per_m2"]==73_740_000
assert ready[0]["review_status"]=="reviewed-release"
assert "candidate_only" not in ready[0]
assert not release.validate_history(history+ready,baseline)
duplicate,decisions,problems=release.evaluate(history+ready,baseline,queue,s2["data"],[approval],today)
assert not duplicate and decisions[0]["status"]=="already-published" and not problems

def reject(edited,checkdata=None,wanted=None):
    extra,decisions,problems=release.evaluate(history,baseline,queue,
        s2["data"] if checkdata is None else checkdata,[edited],today)
    assert not extra and decisions[0]["status"]=="blocked"
    if wanted:assert wanted in decisions[0]["issues"],(wanted,decisions[0]["issues"])
changed=copy.deepcopy(approval);changed["checked_source_evidence"]=False
reject(changed,wanted="source-evidence-not-approved")
changed=copy.deepcopy(approval);changed["verification_run_ids"]=["111","222"]
reject(changed,wanted="approved-rechecks-not-last-two-observations")
changed=copy.deepcopy(approval);changed["review_date"]="2026-12-01"
reject(changed,wanted="review-from-future")
changed=copy.deepcopy(approval);changed["review_note"]="OK"
reject(changed,wanted="review-note-too-short")
badrecord=copy.deepcopy(s2["data"])
badrecord[0]["checks"][-1]["status"]="source-revised-same-period"
reject(approval,checkdata=badrecord,wanted="latest-rechecks-did-not-match-publisher")
badrecord=copy.deepcopy(s2["data"])
badrecord[0]["checks"][-1]["checked_at"]="2026-10-09T02:30:00+00:00"
reject(approval,checkdata=badrecord,wanted="independent-source-rechecks-too-close")
tampered=copy.deepcopy(lumiere)
tampered["subproject_name"]="Masteri Centre Point"
assert not release.candidate_in_series(tampered,base)
tampered=copy.deepcopy(lumiere)
tampered["value_vnd_per_m2"]=88_000_000
assert not release.candidate_in_series(tampered,base)
tampered=copy.deepcopy(lumiere)
tampered["source_url"]="https://other.example/"
assert not release.candidate_in_series(tampered,base)
changed_baseline=copy.deepcopy(history)
changed_baseline[0]["review_status"]="reviewed-release"
assert release.validate_history(changed_baseline,baseline)
assert load("data/mock/market/alternative-monthly-history.json")["record_count"]==1
assert load("data/mock/market/listing-observations.json")["record_count"]==18
print("PASS: two indexed subproject baselines remain isolated; exact month/source rechecks, independent-run proof, tampering and duplicate releases enforced.")
