"""Release only explicitly approved, twice-rechecked subproject-specific monthly asking rates.

September 2026 indexed baselines remain distinguishable from true source HTML
rechecks. Publication here never alters parent project ASP, Batdongsan
listing snapshots, or OneHousing Vinhomes Grand Park parent history.
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import date,datetime,timedelta
from pathlib import Path
from market_subproject_candidate_recheck import content_signature
import market_alternative_auto_probe as probe

ROOT=Path(__file__).resolve().parents[1]
HISTORY=ROOT/"data/mock/market/alternative-subproject-monthly-history.json"
BASELINES=ROOT/"data/mock/market/alternative-subproject-monthly-evidence.json"
QUEUE=ROOT/"data/candidate/market/alternative-price-review-queue.json"
VERIFICATION=ROOT/"data/state/alternative-candidate-verification.json"
APPROVALS=ROOT/"config/market-subproject-reviewed-approvals.json"
REPORT=ROOT/"data/candidate/market/subproject-monthly-release-report.json"
MONTH=re.compile(r"20\d{2}-(0[1-9]|1[0-2])$")
PRICE=re.compile(r"(\d+(?:[.,]\d+)?)\s*triệu\s*/?\s*m[²2]",re.I)
RANGE=re.compile(r"Khoảng giá\s*[:|]?\s*(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*triệu",re.I)
HEADER=re.compile(r"Căn hộ chung cư dự án\s+(.+?)\s+tháng\s+(\d{1,2})/(20\d{2})",re.I)

def quote_matches(row):
    e=row.get("evidence",{})
    h=HEADER.search(e.get("period",""))
    p=PRICE.search(e.get("metric",""))
    rng=RANGE.search(e.get("range",""))
    if not all((h,p,rng)):
        return False
    return (probe.normal_name(h.group(1))==probe.normal_name(row.get("subproject_name",""))
            and f"{h.group(3)}-{int(h.group(2)):02d}"==row.get("period")
            and probe.vnd(p.group(1))==row.get("value_vnd_per_m2")
            and probe.vnd(rng.group(1))==row.get("range_low_vnd_per_m2")
            and probe.vnd(rng.group(2))==row.get("range_high_vnd_per_m2")
            and 0<row["range_low_vnd_per_m2"]<=row["value_vnd_per_m2"]<=row["range_high_vnd_per_m2"]<=1_000_000_000)

def baseline_map(baselines):
    return {r["id"]:r for r in baselines}

def candidate_in_series(candidate,base):
    keys=("project_id","source_id","source_url","asset_type","metric_type","period_type","subproject_name")
    return (base is not None and all(candidate.get(k)==base.get(k) for k in keys)
            and candidate.get("baseline_record_id")==base.get("id")
            and candidate.get("candidate_only") is True
            and candidate.get("review_required") is True
            and candidate.get("review_date") is None
            and bool(MONTH.fullmatch(candidate.get("period","")))
            and quote_matches(candidate)
            and candidate["period"] > base["period"])

def validate_history(history,baselines):
    errors=[]
    bmap=baseline_map(baselines)
    if len(bmap)!=2 or len(history)<2:
        errors.append("missing-two-distinct-indexed-subproject-baselines")
    observations={}
    for row in history:
        sid=row.get("source_record_id")
        base=bmap.get(sid)
        if base is None or not quote_matches(row):
            errors.append("unknown-or-bad-quoted-subproject-history")
            continue
        if any(row.get(k)!=base.get(k) for k in ("project_id","source_id","source_url","subproject_name","asset_type","metric_type")):
            errors.append("source-or-subproject-changed")
        if row.get("series_key") != f"onehousing-{base['subproject_id']}-apartment-popular-asking":
            errors.append("wrong-series-key")
        if row.get("period") in observations.setdefault(sid,set()):
            errors.append("duplicate-period-within-series")
        observations[sid].add(row.get("period"))
        if row.get("period")==base["period"]:
            if any(row.get(k)!=base.get(k) for k in ("value_vnd_per_m2","range_low_vnd_per_m2","range_high_vnd_per_m2","evidence")):
                errors.append("indexed-baseline-drift")
            if row.get("review_status")!="source-indexed-baseline":
                errors.append("indexed-baseline-misrepresented")
        elif row.get("review_status")!="reviewed-release" or row.get("period","")<=base["period"]:
            errors.append("not-approved-after-indexed-baseline")
    for b in bmap.values():
        if b["period"] not in observations.get(b["id"],set()):
            errors.append("missing-original-series-period")
    return errors

def verification_proofs(record,candidate,approval):
    errors=[]
    if not record:
        return ["missing-independent-publisher-rechecks"]
    signature=content_signature(candidate)
    if record.get("candidate_signature")!=signature:
        errors.append("candidate-verified-content-drift")
    checks=record.get("checks",[])
    ids=approval.get("verification_run_ids")
    if not isinstance(ids,list) or len(ids)!=2 or len(set(ids))!=2 or not all(str(x).isdigit() for x in ids):
        errors.append("must-approve-two-distinct-workflow-runs")
    elif len(checks)<2 or [x.get("run_id") for x in checks[-2:]] != [str(i) for i in ids]:
        errors.append("approved-rechecks-not-last-two-observations")
    if len(checks)>=2:
        pair=checks[-2:]
        if any(x.get("status")!="matched-source-period-and-metric" or x.get("candidate_signature")!=signature
               or x.get("source_http_status")!=200 or
               x.get("source_final_host") not in ("onehousing.vn","beta.onehousing.vn")
               for x in pair):
            errors.append("latest-rechecks-did-not-match-publisher")
        try:
            d1=datetime.fromisoformat(pair[0]["checked_at"])
            d2=datetime.fromisoformat(pair[1]["checked_at"])
            if d2-d1 < timedelta(hours=1):
                errors.append("independent-source-rechecks-too-close")
        except (ValueError,KeyError,TypeError):
            errors.append("bad-source-recheck-times")
    return errors

def evaluate(history,baselines,queue,rechecks,approvals,today):
    problems=validate_history(history,baselines)
    existing={(r.get("source_record_id"),r.get("period")):r for r in history}
    by_base=baseline_map(baselines)
    queue_by_id={r.get("id"):r for r in queue}
    records={r.get("candidate_id"):r for r in rechecks}
    decisions=[]; ready=[]; used_approvals=set()
    for approval in approvals:
        cid=approval.get("candidate_id")
        issues=[]
        if not cid or cid in used_approvals:
            issues.append("duplicate-or-missing-approval")
        used_approvals.add(cid)
        candidate=queue_by_id.get(cid)
        if not candidate:
            issues.append("candidate-not-in-source-review-queue")
        if approval.get("checked_source_evidence") is not True:
            issues.append("source-evidence-not-approved")
        if len(str(approval.get("review_note","")).strip())<30:
            issues.append("review-note-too-short")
        try:
            reviewed=date.fromisoformat(approval.get("review_date",""))
            if reviewed>today:
                issues.append("review-from-future")
        except ValueError:
            issues.append("invalid-review-date");reviewed=None
        if candidate:
            base=by_base.get(candidate.get("baseline_record_id"))
            if not candidate_in_series(candidate,base):
                issues.append("wrong-series-source-or-quoted-metrics")
            if reviewed and candidate.get("period","")>reviewed.strftime("%Y-%m"):
                issues.append("candidate-period-after-review")
            issues.extend(verification_proofs(records.get(cid),candidate,approval))
            key=(candidate.get("baseline_record_id"),candidate.get("period"))
            current=existing.get(key)
            if current:
                if not issues and current.get("value_vnd_per_m2")==candidate.get("value_vnd_per_m2") and current.get("review_status")=="reviewed-release":
                    decisions.append({"candidate_id":cid,"status":"already-published","issues":[]})
                    continue
                issues.append("existing-period-cannot-be-overwritten")
            if not issues:
                series_key=f"onehousing-{base['subproject_id']}-apartment-popular-asking"
                row={k:candidate.get(k) for k in (
                    "id","project_id","source_id","source_url","subproject_name",
                    "asset_type","metric_type","period_type","period","value_vnd_per_m2",
                    "range_low_vnd_per_m2","range_high_vnd_per_m2","source_publication_date","evidence","methodology_note")}
                row.update(series_key=series_key,source_record_id=base["id"],review_date=approval["review_date"],
                           review_note=approval["review_note"],review_status="reviewed-release",
                           verification_run_ids=approval["verification_run_ids"])
                ready.append(row)
                existing[key]=row
        decisions.append({"candidate_id":cid,"status":"blocked" if issues else "ready","issues":issues})
    return ready,decisions,problems

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("preview","promote"),default="preview")
    p.add_argument("--today",default=date.today().isoformat())
    args=p.parse_args()
    history=probe.load(HISTORY)
    baselines=probe.load(BASELINES)
    queue=probe.load(QUEUE)
    approvals=probe.load(APPROVALS)
    rechecks=probe.load(VERIFICATION) if VERIFICATION.exists() else {"data":[]}
    if any(x.get("record_count")!=len(x.get("data",[])) for x in (history,baselines,queue,approvals,rechecks)):
        raise SystemExit("Count mismatch in subproject history/recheck/approval contracts")
    ready,decisions,problems=evaluate(history["data"],baselines["data"],queue["data"],rechecks["data"],approvals["data"],date.fromisoformat(args.today))
    report={"mode":args.mode,"checked_date":args.today,"indexed_subproject_baselines":2,
            "approvals_checked":len(approvals["data"]),"eligible_new_months":len(ready),
            "blocked_approvals":sum(d["status"]=="blocked" for d in decisions),
            "validation_issues":problems,"decisions":decisions,
            "production_changed":False}
    if args.mode=="promote" and ready and not problems and not report["blocked_approvals"]:
        history["data"].extend(ready)
        history["record_count"]=len(history["data"])
        probe.save(HISTORY,history)
        report["production_changed"]=True
    probe.save(REPORT,report)
    if problems or report["blocked_approvals"]:
        raise SystemExit(json.dumps(report,ensure_ascii=False))
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":main()
