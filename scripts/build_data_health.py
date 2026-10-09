#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
OPS=ROOT/"config/operations_health.json"
MATRIX=ROOT/"config/update_matrix.json"
OUT=ROOT/"data/state/data-health.json"

def load(path,default=None):
    p=Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

def dump(path,obj):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def parse_dt(v):
    if not v: return None
    s=str(v)
    if s.endswith("Z"): s=s[:-1]+"+00:00"
    try:
        d=datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None

def now_iso(): return datetime.now(timezone.utc).isoformat()

def business_days_elapsed(start: date, end: date) -> int:
    """Count working days *after* the source date, excluding weekends.

    Public-holiday gaps are not guessed; this is an operational prompt for
    review, never a claim that new market data must exist.
    """
    if start > end:
        return 0
    total = 0
    cursor = start
    while cursor < end:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            total += 1
    return total


def source_observation(entry, rows, as_of):
    """Separate publisher observation staleness from repository write age."""
    selected = rows
    if entry.get("id") == "macro-daily-markets":
        valid = [r for r in selected
                 if r.get("period_type") == "day"
                 and r.get("period") and r.get("observation_status") == "final"]
        dates = []
        for row in valid:
            try:
                dates.append(date.fromisoformat(row["data_date"] or row["period"]))
            except (ValueError, TypeError):
                continue
        if not dates:
            return {"latest_source_period": None, "source_business_day_lag": None,
                    "source_freshness": "unknown"}
        last = max(dates)
        today = as_of.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
        lag = business_days_elapsed(last, today)
        return {"latest_source_period": last.isoformat(),
                "source_business_day_lag": lag,
                "source_freshness": "late" if lag > 1 else "within-window"}
    periods = sorted([str(r["period"]) for r in selected if r.get("period")])
    return {"latest_source_period": periods[-1] if periods else None,
            "source_business_day_lag": None, "source_freshness": "release-based"}


def trusted_run_url(run):
    url = run.get("html_url")
    if not isinstance(url, str):
        return None
    parsed = urlparse(url)
    chunks = parsed.path.strip("/").split("/")
    if (parsed.scheme == "https" and parsed.netloc == "github.com"
        and len(chunks) == 5 and chunks[2:4] == ["actions", "runs"]
        and chunks[4].isdigit() and not parsed.query and not parsed.fragment):
        return url
    return None


def prod_info(entry,matrix_by_id,as_of):
    m=matrix_by_id.get(entry["id"],{})
    path=entry.get("production_path") or m.get("data_path")
    payload=load(ROOT/path,{"data":[]}) if path else {"data":[]}
    rows=payload.get("data",[]) if isinstance(payload,dict) else []
    if not isinstance(rows,list): rows=[]
    indicator_ids=set(m.get("indicator_ids") or [])
    if indicator_ids:
        rows=[r for r in rows if r.get("indicator_id") in indicator_ids]
    stamp=payload.get("generated_at") or payload.get("updated_at")
    dt=parse_dt(stamp)
    stale=entry.get("stale_after_hours",m.get("stale_after_hours"))
    age=None if not dt else round((as_of-dt.astimezone(timezone.utc)).total_seconds()/3600,1)
    freshness="unknown"
    if dt and stale is None: freshness="current"
    elif dt and age<=stale: freshness="fresh"
    elif dt and age<=stale*1.25: freshness="due"
    elif dt: freshness="stale"
    return {"production_path":path,"record_count":len(rows),"last_production_at":stamp,"age_hours":age,"stale_after_hours":stale,"freshness":freshness,**source_observation(entry,rows,as_of)}

def market_obs_backlog(candidate_path):
    cand=load(ROOT/candidate_path,{"data":[]}).get("data",[])
    prod=load(ROOT/"data/mock/market/observations.json",{"data":[]}).get("data",[])
    def key(x): return (x.get("scope_type"),tuple(x.get("region_ids") or []),tuple(x.get("segment_ids") or []),x.get("period"),x.get("source_id"))
    fields=("new_supply","new_supply_lower_bound","sales_units","absorption_rate","average_asp","asp_unit","currency","price_basis","metric_qualifiers")
    by={key(x):x for x in prod}
    pending=conflicts=0
    for x in cand:
        p=by.get(key(x))
        if p is None: pending+=1
        elif any(p.get(f)!=x.get(f) for f in fields): conflicts+=1
    return pending+conflicts,conflicts

def generic_backlog(candidate_path):
    payload=load(ROOT/candidate_path,{"data":[]})
    rows=payload.get("data",[]) if isinstance(payload,dict) else []
    return len(rows),0

def candidate_info(entry):
    path=entry.get("candidate_path")
    if not path:
        return {"candidate_path":None,"candidate_state":entry.get("candidate_mode","none"),"candidate_backlog":None,"candidate_conflicts":0,"last_candidate_at":None}
    payload=load(ROOT/path,None)
    if payload is None:
        return {"candidate_path":path,"candidate_state":"not-persisted","candidate_backlog":0,"candidate_conflicts":0,"last_candidate_at":None}
    mode=entry.get("candidate_mode")
    if mode=="market-observations": backlog,conflicts=market_obs_backlog(path)
    else: backlog,conflicts=generic_backlog(path)
    return {"candidate_path":path,"candidate_state":"persisted","candidate_backlog":backlog,"candidate_conflicts":conflicts,"last_candidate_at":payload.get("generated_at")}

def load_runs(args, ops):
    if args.workflow_runs_fixture:
        return load(Path(args.workflow_runs_fixture),{"workflow_runs":[]}).get("workflow_runs",[])
    repo=os.getenv("GITHUB_REPOSITORY")
    token=os.getenv("GITHUB_TOKEN")
    if not repo: return []
    headers={"Accept":"application/vnd.github+json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    files=sorted({x.get("workflow_file") for x in ops.get("datasets",[]) if x.get("workflow_file")})
    runs=[]
    for workflow_file in files:
        url=f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/runs?per_page=20"
        r=requests.get(url,headers=headers,timeout=20)
        if r.status_code==404:
            continue
        r.raise_for_status()
        runs.extend(r.json().get("workflow_runs",[]))
    return runs

def workflow_info(name,runs):
    # A failed PR test must not be reported as a failed production collector.
    matches=[x for x in runs if x.get("name")==name and
             x.get("head_branch") in ("main",None)]
    matches.sort(key=lambda x:x.get("created_at") or "",reverse=True)
    latest=matches[0] if matches else None
    success=next((x for x in matches if x.get("conclusion")=="success"),None)
    if not latest:
        return {"workflow_status":"unknown","last_workflow_run_at":None,
                "last_successful_run_at":None,"last_workflow_run_url":None,
                "last_workflow_conclusion":None,"recent_attempts":[]}
    if latest.get("status")!="completed": status="running"
    elif latest.get("conclusion")=="success": status="healthy"
    else: status="degraded"
    recent=[{
        "status":r.get("status"),"conclusion":r.get("conclusion"),
        "at":r.get("updated_at") or r.get("created_at"),
        "url":trusted_run_url(r)
    } for r in matches[:3]]
    return {
      "workflow_status":status,
      "last_workflow_run_at":latest.get("updated_at") or latest.get("created_at"),
      "last_successful_run_at":(success or {}).get("updated_at") or (success or {}).get("created_at"),
      "last_workflow_run_url":trusted_run_url(latest),
      "last_workflow_conclusion":latest.get("conclusion"),
      "recent_attempts":recent
    }

def row_status(prod,cand,wf):
    if prod["freshness"]=="stale" or prod["source_freshness"]=="late": return "stale"
    if wf["workflow_status"]=="degraded": return "degraded"
    if wf["workflow_status"]=="running": return "running"
    if (cand.get("candidate_backlog") or 0)>0 or (cand.get("candidate_conflicts") or 0)>0: return "review"
    if prod["freshness"] in {"due","unknown"}: return "review"
    return "healthy"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default=str(OUT))
    ap.add_argument("--workflow-runs-fixture")
    ap.add_argument("--as-of")
    args=ap.parse_args()
    as_of=parse_dt(args.as_of) if args.as_of else datetime.now(timezone.utc)
    ops=load(OPS); matrix=load(MATRIX)
    matrix_by={x["id"]:x for x in matrix.get("datasets",[])}
    runs=load_runs(args,ops)
    rows=[]
    for entry in ops["datasets"]:
        prod=prod_info(entry,matrix_by,as_of)
        cand=candidate_info(entry)
        wf=workflow_info(entry["workflow_name"],runs)
        status=row_status(prod,cand,wf)
        rows.append({**entry,**prod,**cand,**wf,"status":status,"failure_behavior":matrix_by.get(entry["id"],{}).get("failure_behavior","retain-last-good")})
    rank={"healthy":0,"running":1,"review":2,"degraded":3,"stale":4}
    modules=[]
    for mod in ops["modules"]:
        rs=[x for x in rows if x["module"]==mod]
        worst=max(rs,key=lambda x:rank.get(x["status"],2))["status"] if rs else "review"
        modules.append({"module":mod,"status":worst,"dataset_count":len(rs),"candidate_backlog":sum(x.get("candidate_backlog") or 0 for x in rs),"last_successful_run_at":max([x.get("last_successful_run_at") or "" for x in rs] or [""]) or None,"last_production_at":max([x.get("last_production_at") or "" for x in rs] or [""]) or None})
    overall=max(modules,key=lambda x:rank.get(x["status"],2))["status"] if modules else "review"
    out={"schema_version":1,"generated_at":as_of.isoformat(),"overall_status":overall,"modules":modules,"datasets":rows}
    dump(args.output,out)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
