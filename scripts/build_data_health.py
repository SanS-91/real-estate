#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
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

def prod_info(entry,matrix_by_id,as_of):
    m=matrix_by_id.get(entry["id"],{})
    path=entry.get("production_path") or m.get("data_path")
    payload=load(ROOT/path,{"data":[]}) if path else {"data":[]}
    rows=payload.get("data",[]) if isinstance(payload,dict) else []
    stamp=payload.get("generated_at") or payload.get("updated_at")
    dt=parse_dt(stamp)
    stale=entry.get("stale_after_hours",m.get("stale_after_hours"))
    age=None if not dt else round((as_of-dt.astimezone(timezone.utc)).total_seconds()/3600,1)
    freshness="unknown"
    if dt and stale is None: freshness="current"
    elif dt and age<=stale: freshness="fresh"
    elif dt and age<=stale*1.25: freshness="due"
    elif dt: freshness="stale"
    return {"production_path":path,"record_count":len(rows),"last_production_at":stamp,"age_hours":age,"stale_after_hours":stale,"freshness":freshness}

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

def load_runs(args):
    if args.workflow_runs_fixture:
        return load(Path(args.workflow_runs_fixture),{"workflow_runs":[]}).get("workflow_runs",[])
    repo=os.getenv("GITHUB_REPOSITORY")
    token=os.getenv("GITHUB_TOKEN")
    if not repo: return []
    headers={"Accept":"application/vnd.github+json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    r=requests.get(f"https://api.github.com/repos/{repo}/actions/runs?per_page=100",headers=headers,timeout=20)
    r.raise_for_status()
    return r.json().get("workflow_runs",[])

def workflow_info(name,runs):
    matches=[x for x in runs if x.get("name")==name]
    matches.sort(key=lambda x:x.get("created_at") or "",reverse=True)
    latest=matches[0] if matches else None
    success=next((x for x in matches if x.get("conclusion")=="success"),None)
    if not latest:
        return {"workflow_status":"unknown","last_workflow_run_at":None,"last_successful_run_at":None}
    if latest.get("status")!="completed": status="running"
    elif latest.get("conclusion")=="success": status="healthy"
    else: status="degraded"
    return {
      "workflow_status":status,
      "last_workflow_run_at":latest.get("updated_at") or latest.get("created_at"),
      "last_successful_run_at":(success or {}).get("updated_at") or (success or {}).get("created_at")
    }

def row_status(prod,cand,wf):
    if prod["freshness"]=="stale": return "stale"
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
    runs=load_runs(args)
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
