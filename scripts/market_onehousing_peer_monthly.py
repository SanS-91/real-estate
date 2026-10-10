"""Publisher-authored HCMC peer comparable monthly rates; fail-closed 2-run gate.

These three source targets are NOT members of Market's curated 13 project
registry. Nothing here feeds project ASP, developer summaries or supply/sales.
PR probes are read-only; production only publishes exact publisher evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import requests
import market_alternative_auto_probe as provider

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/market-onehousing-peer-monthly-targets.json"
HISTORY=ROOT/"data/mock/market/peer-project-monthly-verified.json"
STATE=ROOT/"data/state/market-onehousing-peer-monthly-verification.json"
HEALTH=ROOT/"data/state/market-onehousing-peer-monthly-health.json"
MIN_SECONDS=3600
KEYS=("value_vnd_per_m2","range_low_vnd_per_m2","range_high_vnd_per_m2")


def safe_target(target):
    parsed=urlsplit(target.get("url",""))
    return (target.get("source_id")=="onehousing-vn" and
            target.get("asset_type")=="apartment" and
            target.get("metric_type")=="popular-asking-price-per-sqm" and
            target.get("publisher_project_name") and target.get("id") and
            parsed.scheme=="https" and parsed.hostname=="onehousing.vn" and
            not parsed.query and not parsed.fragment and not parsed.username and
            not parsed.password and
            parsed.path.startswith("/phan-tich/du-an/can-ho-chung-cu-du-an-"))


def publisher_probe(target,session,today):
    if not safe_target(target):
        return {"status":"invalid-publisher-target"},None
    access,html=provider.fetch_html(target,session)
    if not html or access.get("http_status")!=200:
        return {"status":access.get("status","unreachable"),"http_status":access.get("http_status")},None
    clean=provider.plain_text(html)
    rate=provider.onehousing_monthly(clean,today,target["publisher_project_name"])
    diag=provider.onehousing_source_diagnostics(clean,target["publisher_project_name"])
    if rate is None:
        return {"status":"unverifiable-project-month","http_status":200,
                "exact_project_header":diag["publisher_project_header"],
                "price_sections":diag["page_level_price_sections"],
                "other_project_headers":diag["other_publisher_project_headers"],
                "login_wall_visible":diag["login_wall_in_text"]},None
    return {"status":"publisher-month-parsed","http_status":200,
            "source_period":rate["period"],"exact_project_header":True},rate


def fingerprint(target,observation):
    obj={"target":target["id"],"url":target["url"],"publisher_project_name":target["publisher_project_name"],
         "source_id":"onehousing-vn","asset_type":"apartment","metric_type":"popular-asking-price-per-sqm",
         "period":observation["period"],**{k:observation[k] for k in KEYS}}
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def eligible_observation(target,obs,today):
    if not safe_target(target) or not isinstance(obs,dict):
        return False
    period=obs.get("period")
    if not isinstance(period,str) or len(period)!=7 or not period[:4].isdigit() or period[4]!="-":
        return False
    try:
        year,month=map(int,period.split("-"))
        start=date(year,month,1)
    except (ValueError,OverflowError):
        return False
    lag=(today.year-year)*12 + today.month-month
    if lag<0 or lag>3:
        return False
    v=[obs.get(k) for k in KEYS]
    return (all(isinstance(x,int) and not isinstance(x,bool) for x in v) and
            0<v[1]<=v[0]<=v[2]<=1_000_000_000)


def evaluate(config,state,history,parsed_by_id,now,run_id):
    """Pure update with a single current source period per peer; never interpolate."""
    candidates=dict((state or {}).get("candidates",{}))
    records=list(history.get("data",[]))
    if history.get("record_count",len(records))!=len(records):
        raise ValueError("history record_count mismatch")
    status=[]
    newly_verified=[]
    today=now.date()
    for target in config["targets"]:
        if not safe_target(target):
            status.append({"id":target.get("id","unknown"),"status":"invalid-target"})
            continue
        observed=parsed_by_id.get(target["id"])
        check,obs=observed if observed is not None else ({"status":"not-checked"},None)
        if not eligible_observation(target,obs,today):
            status.append({"id":target["id"],"status":check.get("status","unverifiable"),
                           "source_period":check.get("source_period"),
                           "http_status":check.get("http_status")})
            continue
        period=obs["period"]
        record_id=f"peer-onehousing-{target['id']}-{period}"
        fp=fingerprint(target,obs)
        same=[r for r in records if r["target_id"]==target["id"] and r["period"]==period]
        if same:
            if len(same)!=1 or same[0]["fingerprint"]!=fp:
                status.append({"id":target["id"],"status":"published-period-conflict","source_period":period})
            else:
                status.append({"id":target["id"],"status":"published-period-unchanged","source_period":period})
            continue
        prior=[r for r in records if r["target_id"]==target["id"]]
        if prior and period<=max(r["period"] for r in prior):
            status.append({"id":target["id"],"status":"older-than-published","source_period":period})
            continue
        if prior:
            old=max(prior,key=lambda x:x["period"])
            rate=obs["value_vnd_per_m2"]/old["value_vnd_per_m2"]
            if rate<0.7 or rate>1.3:
                status.append({"id":target["id"],"status":"price-change-outlier-review","source_period":period})
                continue
        key=target["id"]+"|"+period
        previous=candidates.get(key)
        if previous is not None and previous["fingerprint"]!=fp:
            # Same source-month has conflicting prices. Do not reset proof
            # toward a different fingerprint, even after more source runs.
            previous["conflict"]=True
            status.append({"id":target["id"],"status":"candidate-period-price-conflict","source_period":period})
            continue
        if previous is None:
            previous={"fingerprint":fp,"period":period,"target_id":target["id"],
                      "first_checked_at":now.isoformat(),"checks":[],"conflict":False}
            candidates[key]=previous
        if previous["conflict"]:
            status.append({"id":target["id"],"status":"candidate-period-price-conflict","source_period":period})
            continue
        if str(run_id) not in [x["run_id"] for x in previous["checks"]]:
            previous["checks"].append({"run_id":str(run_id),"checked_at":now.isoformat()})
        times=sorted(datetime.fromisoformat(x["checked_at"]) for x in previous["checks"])
        valid=len(times)>=2 and (times[-1]-times[0]).total_seconds()>=MIN_SECONDS
        if not valid:
            status.append({"id":target["id"],"status":"awaiting-independent-hosted-check",
                           "source_period":period,"check_count":len(times)})
            continue
        accepted={"id":record_id,"target_id":target["id"],"project_name":target["name"],
                  "source_id":"onehousing-vn","source_url":target["url"],
                  "asset_type":"apartment","metric_type":"popular-asking-price-per-sqm",
                  "scope_type":"separate-hcm-peer-comparable","period":period,"period_type":"month",
                  **{k:obs[k] for k in KEYS},"fingerprint":fp,
                  "review_status":"automated-two-hosted-checks",
                  "verified_at":now.isoformat(),
                  "verification_run_ids":[x["run_id"] for x in previous["checks"]],
                  "methodology_note":"Source-authored apartment popular asking rate per m² for this exact separate HCMC peer. Two matching GitHub-hosted checks >=1h apart. Not transaction ASP or a core registry project."}
        records.append(accepted)
        newly_verified.append(record_id)
        status.append({"id":target["id"],"status":"new-month-verified","source_period":period})
    records.sort(key=lambda r:(r["target_id"],r["period"]))
    new_state={"schema_version":1,"candidates":candidates}
    new_history={**history,"record_count":len(records),"data":records}
    health={"schema_version":1,"generated_at":now.isoformat(),"targets_checked":len(config["targets"]),
            "exact_publisher_months_parsed":sum(eligible_observation(t,parsed_by_id[t["id"]][1],today)
                for t in config["targets"] if t["id"] in parsed_by_id),
            "new_verified_months":len(newly_verified),"published_months":len(records),
            "projects_with_verified_month":len({r["target_id"] for r in records}),
            "checks":status,"candidate_only_unless_two_hosted_checks":True,
            "methodology":"HCMC publisher-priced peers outside core 13. No price value is displayed before two independent matching checks >=1 hour apart."}
    return new_state,new_history,health


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preview",action="store_true")
    ap.add_argument("--run-id",default=os.getenv("GITHUB_RUN_ID","local"))
    args=ap.parse_args()
    cfg=provider.load(CONFIG)
    if len({x["id"] for x in cfg["targets"]})!=len(cfg["targets"]):
        raise ValueError("duplicate target IDs")
    now=datetime.now(timezone.utc)
    observations={}
    with requests.Session() as sess:
        for target in cfg["targets"]:
            observations[target["id"]]=publisher_probe(target,sess,now.date())
    current=provider.load(HISTORY)
    previous=provider.load(STATE) if STATE.exists() else {"schema_version":1,"candidates":{}}
    updated,hist,health=evaluate(cfg,previous,current,observations,now,args.run_id)
    health["check_urls"]=[{"id":t["id"],"host":urlsplit(t["url"]).hostname} for t in cfg["targets"]]
    print(json.dumps({"preview":args.preview,"health":health},ensure_ascii=False))
    if args.preview or os.getenv("GITHUB_EVENT_NAME")=="pull_request":
        return
    provider.save(STATE,updated)
    provider.save(HISTORY,hist)
    provider.save(HEALTH,health)

if __name__=="__main__":
    main()
