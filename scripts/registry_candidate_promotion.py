#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEGAL_PROD=ROOT/"data/mock/legal/documents.json"
LEGAL_CAND=ROOT/"data/candidate/legal/documents.json"
INFRA_PROJECTS=ROOT/"data/mock/infrastructure/projects.json"
INFRA_SCHEDULES=ROOT/"data/mock/infrastructure/schedules.json"
INFRA_CAND=ROOT/"data/candidate/infrastructure/updates.json"
REPORT=ROOT/"data/candidate/registry/promotion-report.json"

def load(p,default=None):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else default

def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def now(): return datetime.now(timezone.utc).isoformat()

def legal_key(row):
    return str(row.get("document_number") or "").upper()

def canonical_legal_id(row):
    base=legal_key(row).lower()
    base=base.replace("đ","d")
    base=re.sub(r"[^a-z0-9]+","-",base).strip("-")
    return "legal-"+base

def legal_preview(prod,cands):
    by={legal_key(x):x for x in prod if legal_key(x)}
    out=[]
    for c in cands:
        issues=list(c.get("review_issues") or [])
        k=legal_key(c)
        prev=by.get(k)
        if issues:
            status="review-required"
        elif not k:
            status="invalid"
        elif prev is None:
            status="new"
        else:
            fields=["title","document_type","status","agency_ids","scope_type","region_ids","topic_ids","issued_date","effective_date","official_url"]
            changed={f:{"from":prev.get(f),"to":c.get(f)} for f in fields if prev.get(f)!=c.get(f)}
            status="unchanged" if not changed else "conflict"
        out.append({"id":c.get("id"),"document_number":c.get("document_number"),"status":status,"review_issues":issues})
    return out

def promote_legal(prod_payload,cands,decisions):
    blocked=[x for x in decisions if x["status"] in {"review-required","invalid","conflict"}]
    if blocked: raise SystemExit("Refusing legal promotion: unresolved review/conflict")
    out=copy.deepcopy(prod_payload); existing={legal_key(x) for x in out.get("data",[])}
    added=0
    for c,d in zip(cands,decisions):
        if d["status"]!="new": continue
        row={k:v for k,v in c.items() if k not in {"review_issues","collector_provenance"}}
        row["id"]=canonical_legal_id(row)
        row.setdefault("created_at",now()); row["updated_at"]=now()
        out["data"].append(row); existing.add(legal_key(row)); added+=1
    out["data"].sort(key=lambda x:(x.get("issued_date") or "",x.get("document_number") or ""),reverse=True)
    out["record_count"]=len(out["data"]); out["generated_at"]=now(); out["build_id"]="phase5.7c-legal-promotion"
    return out,added

def schedule_identity(x):
    return (x.get("infrastructure_project_id"),x.get("schedule_type"),x.get("target_period"),x.get("source_url"))

def infra_preview(projects,schedules,cands):
    pmap={x["id"]:x for x in projects}
    skeys={schedule_identity(x) for x in schedules}
    out=[]
    for c in cands:
        issues=list(c.get("review_issues") or [])
        pid=c.get("project_id")
        sched=c.get("schedule_candidate")
        patch=c.get("project_patch") or {}
        sched_status=None
        if sched:
            sched_status="unchanged" if schedule_identity(sched) in skeys else "new"
        patch_changes={}
        if pid in pmap:
            patch_changes={k:{"from":pmap[pid].get(k),"to":v} for k,v in patch.items() if pmap[pid].get(k)!=v}
        patch_status="changed" if patch_changes else ("unchanged" if patch else None)
        status="review-required" if issues else ("new" if sched_status=="new" or patch_status=="changed" else "unchanged")
        out.append({"id":c.get("id"),"project_id":pid,"status":status,"schedule_status":sched_status,"patch_status":patch_status,"review_issues":issues,"patch_changes":patch_changes})
    return out

def stable_schedule_id(s):
    raw="-".join(str(s.get(k) or "") for k in ["infrastructure_project_id","schedule_type","target_period","announced_date"])
    return "schedule-"+re.sub(r"[^a-z0-9]+","-",raw.lower()).strip("-")

def promote_infra(project_payload,schedule_payload,cands,decisions):
    if any(x["status"]=="review-required" for x in decisions):
        raise SystemExit("Refusing infrastructure promotion: unresolved review issues")
    projects=copy.deepcopy(project_payload); schedules=copy.deepcopy(schedule_payload)
    pmap={x["id"]:x for x in projects.get("data",[])}
    existing={schedule_identity(x) for x in schedules.get("data",[])}
    added_sched=0; patched=0
    for c,d in zip(cands,decisions):
        if d["status"]=="unchanged": continue
        pid=c.get("project_id"); project=pmap.get(pid)
        if not project: raise SystemExit(f"Unknown infrastructure project: {pid}")
        patch=c.get("project_patch") or {}
        changed=False
        for k,v in patch.items():
            if project.get(k)!=v:
                project[k]=v; changed=True
        sched=c.get("schedule_candidate")
        if sched and schedule_identity(sched) not in existing:
            ns=copy.deepcopy(sched); ns["id"]=stable_schedule_id(ns); ns["status"]="current"
            for old in schedules.get("data",[]):
                if old.get("infrastructure_project_id")==pid and old.get("schedule_type")==ns.get("schedule_type") and old.get("status")=="current":
                    old["status"]="superseded"
            schedules["data"].append(ns); existing.add(schedule_identity(ns)); added_sched+=1
            if ns.get("schedule_type")=="expected-completion":
                project["current_expected_completion"]=ns.get("target_period")
                project["completion_date_precision"]=ns.get("date_precision")
                changed=True
        if changed: patched+=1
    projects["record_count"]=len(projects.get("data",[])); projects["generated_at"]=now(); projects["build_id"]="phase5.7c-infrastructure-promotion"
    schedules["data"].sort(key=lambda x:(x.get("infrastructure_project_id") or "",x.get("announced_date") or "",x.get("id") or ""))
    schedules["record_count"]=len(schedules.get("data",[])); schedules["generated_at"]=now(); schedules["build_id"]="phase5.7c-infrastructure-promotion"
    return projects,schedules,patched,added_sched

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--module",choices=["legal","infrastructure"],required=True); ap.add_argument("--mode",choices=["preview","promote"],default="preview")
    args=ap.parse_args()
    report={"schema_version":1,"generated_at":now(),"module":args.module,"mode":args.mode,"production_written":False}
    if args.module=="legal":
        prod=load(LEGAL_PROD,{"data":[]}); cands=load(LEGAL_CAND,{"data":[]}).get("data",[])
        decisions=legal_preview(prod.get("data",[]),cands)
        report.update({"candidate_count":len(cands),"decisions":decisions})
        if args.mode=="promote":
            out,added=promote_legal(prod,cands,decisions); dump(LEGAL_PROD,out); report.update({"production_written":True,"added":added})
    else:
        pp=load(INFRA_PROJECTS,{"data":[]}); sp=load(INFRA_SCHEDULES,{"data":[]}); cands=load(INFRA_CAND,{"data":[]}).get("data",[])
        decisions=infra_preview(pp.get("data",[]),sp.get("data",[]),cands)
        report.update({"candidate_count":len(cands),"decisions":decisions})
        if args.mode=="promote":
            np,ns,patched,added=promote_infra(pp,sp,cands,decisions); dump(INFRA_PROJECTS,np); dump(INFRA_SCHEDULES,ns); report.update({"production_written":True,"projects_patched":patched,"schedules_added":added})
    dump(REPORT,report); print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
