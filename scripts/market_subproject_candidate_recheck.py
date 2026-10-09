"""Verify candidate source evidence on independent runs; never publish prices.

This is a *recheck*, not a new market-price observation: its wall-clock date
must not be confused with the publisher-authored price month.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import requests

import market_alternative_auto_probe as provider

ROOT=Path(__file__).resolve().parents[1]
QUEUE=ROOT/"data/candidate/market/alternative-price-review-queue.json"
TARGETS=ROOT/"config/market-alternative-auto-targets.json"
STATE=ROOT/"data/state/alternative-candidate-verification.json"
REPORT=ROOT/"data/candidate/market/alternative-candidate-verification-report.json"
MAX_RECHECKS=8
SOURCE_NAME={
    "onehousing-lumiere-boulevard-apartment":"Lumière Boulevard",
    "onehousing-masteri-centre-point-apartment":"Masteri Centre Point"
}

def content_signature(row):
    fields=(row.get("source_url"),row.get("period"),row.get("source_id"),
            row.get("subproject_name"),row.get("value_vnd_per_m2"),
            row.get("range_low_vnd_per_m2"),row.get("range_high_vnd_per_m2"))
    return hashlib.sha256(json.dumps(fields,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()

def diagnostics(text,project_name):
    titles=[(provider.normal_name(m.group(1)),f"{m.group(3)}-{int(m.group(2)):02d}")
            for m in provider.MONTH_LABEL.finditer(text)]
    matching=[period for title,period in titles if title==provider.normal_name(project_name)]
    return {
        "source_project_header":bool(matching),
        "source_months":sorted(set(matching)),
        "modal_section_present":bool(provider.MODAL_SECTION.search(text)),
        "price_metric_token_present":bool(provider.MODAL.search(text)),
        "asking_range_token_present":bool(provider.RANGE.search(text)),
        "login_wall_visible":"Đăng nhập để xem giá" in text
    }

def evaluate_html(candidate,target,html,today):
    text=provider.plain_text(html)
    parsed=provider.onehousing_monthly(text,today,target["publisher_project_name"])
    diag=diagnostics(text,target["publisher_project_name"])
    if parsed is None:
        return "publisher-metric-unverifiable",diag
    if parsed["period"] != candidate["period"]:
        return ("publisher-older-period" if parsed["period"] < candidate["period"] else "publisher-different-period"),diag
    for field in ("value_vnd_per_m2","range_low_vnd_per_m2","range_high_vnd_per_m2"):
        if parsed[field]!=candidate[field]:
            return "source-revised-same-period",diag
    if candidate.get("source_url") != target["url"] or candidate.get("subproject_name") != target.get("subproject_name"):
        return "candidate-source-project-mismatch",diag
    return "matched-source-period-and-metric",diag

def update_history(previous,candidate,status,source_meta,run_id,checked):
    """Append one independent GitHub-hosted run at most once, never overwrite prior."""
    signature=content_signature(candidate)
    record=previous or {
        "candidate_id":candidate["id"],"source_url":candidate["source_url"],
        "period":candidate["period"],"subproject_name":candidate.get("subproject_name"),
        "candidate_signature":signature,"checks":[]}
    if record.get("candidate_signature") != signature:
        return record, "candidate-content-changed-review-required"
    if any(x.get("run_id")==run_id for x in record["checks"]):
        return record, "duplicate-run-id"
    record["checks"].append({
        "run_id":str(run_id),"checked_at":checked,"status":status,
        "source_http_status":source_meta.get("http_status"),
        "source_final_host":source_meta.get("final_host"),
        "candidate_signature":signature
    })
    record["checks"]=record["checks"][-MAX_RECHECKS:]
    return record, "added"

def current_verified(record):
    checks=record.get("checks",[])
    matching=[x for x in checks if x.get("status")=="matched-source-period-and-metric"]
    return {"matching_run_count":len({x.get("run_id") for x in matching}),
            "latest_source_status":checks[-1]["status"] if checks else "not-checked",
            "latest_matches":bool(checks and checks[-1]["status"]=="matched-source-period-and-metric")}

def run_once(queue,targets,previous,today,run_id,checked,fetcher=provider.fetch_with_publisher_fallback):
    histories={row["candidate_id"]:row for row in previous.get("data",[])}
    target_by_base={x["baseline_id"]:x for x in targets}
    checks=[]
    for candidate in queue:
        cid=candidate.get("id")
        if not cid or candidate.get("metric_type")!="popular-asking-price-per-sqm" or not candidate.get("subproject_name"):
            continue
        target=target_by_base.get(candidate.get("baseline_record_id"))
        if (not target or not provider.allowed_target(target) or
            target.get("subproject_name") != candidate.get("subproject_name") or
            target.get("publisher_project_name") not in SOURCE_NAME.values() or
            target["url"] != candidate.get("source_url")):
            checks.append({"candidate_id":cid,"status":"invalid-source-mapping"})
            continue
        access,html=fetcher(target,requests.Session())
        if html is None:
            status=access.get("status","source-unavailable")
            diag={}
        else:
            status,diag=evaluate_html(candidate,target,html,today)
        prior=histories.get(cid)
        updated,record_status=update_history(prior,candidate,status,access,run_id,checked)
        histories[cid]=updated
        checks.append({"candidate_id":cid,"status":status,"record_status":record_status,
                       "http_status":access.get("http_status"),"diagnostics":diag})
    state={
        "schema_version":1,"generated_at":checked,"source_recheck_only":True,
        "recheck_run_id":str(run_id),"record_count":len(histories),
        "data":sorted(histories.values(),key=lambda x:x["candidate_id"])
    }
    report={"schema_version":1,"generated_at":checked,
            "checked_candidates":len(checks),"production_prices_updated":False,
            "checks":checks}
    return state,report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--today",default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--run-id",default=os.environ.get("GITHUB_RUN_ID","local"))
    args=parser.parse_args()
    from datetime import date
    today=date.fromisoformat(args.today)
    checked=datetime.now(timezone.utc).isoformat()
    queue=provider.load(QUEUE)["data"]
    targets=provider.load(TARGETS)["targets"]
    previous=provider.load(STATE) if STATE.exists() else {"data":[]}
    state,report=run_once(queue,targets,previous,today,args.run_id,checked)
    provider.save(STATE,state)
    provider.save(REPORT,report)
    print(json.dumps({
        "rechecked":report["checked_candidates"],
        "statuses":{x["candidate_id"]:x["status"] for x in report["checks"]},
        "production_price_changes":0},ensure_ascii=False))

if __name__=="__main__":
    main()
