#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/market-historical-backfill.json"
PROD=ROOT/"data/mock/market/observations.json"
SOURCES=ROOT/"data/mock/core/sources.json"
CAND=ROOT/"data/candidate/market/observations.json"
ART=ROOT/"data/candidate/market/articles.json"
REPORT=ROOT/"data/candidate/market/historical-backfill-report.json"

def load(path,default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def dump(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def key(row):
    return (
      row.get("scope_type"),
      tuple(row.get("region_ids") or []),
      tuple(row.get("segment_ids") or []),
      row.get("period"),
      row.get("source_id")
    )

def validate(row,source_ids):
    issues=[]
    for field in ("id","scope_type","period","period_type","source_id","source_date","source_url"):
        if not row.get(field): issues.append(f"missing {field}")
    if row.get("source_id") not in source_ids: issues.append("unknown source_id")
    if not row.get("region_ids"): issues.append("missing region_ids")
    if not row.get("segment_ids"): issues.append("missing segment_ids")
    for field in ("new_supply","new_supply_lower_bound","sales_units","average_asp"):
        value=row.get(field)
        if value is not None and (not isinstance(value,(int,float)) or value<0):
            issues.append(f"invalid {field}")
    absorption=row.get("absorption_rate")
    if absorption is not None and (not isinstance(absorption,(int,float)) or absorption<0 or absorption>1):
        issues.append("invalid absorption_rate")
    return issues

def main():
    cfg=load(CONFIG,{"records":[]})
    prod=load(PROD,{"data":[]}).get("data",[])
    source_ids={x["id"] for x in load(SOURCES,{"data":[]}).get("data",[])}
    prod_by={key(x):x for x in prod}
    candidate=[]; decisions=[]; errors=[]
    seen=set()
    for row in cfg.get("records",[]):
        k=key(row)
        row_issues=validate(row,source_ids)
        if k in seen: row_issues.append("duplicate backfill key")
        seen.add(k)
        if row_issues:
            errors.extend([f"{row.get('id','?')}: {x}" for x in row_issues])
            decisions.append({"id":row.get("id"),"status":"invalid","issues":row_issues})
            continue
        prior=prod_by.get(k)
        if prior is None:
            status="new"; candidate.append(row)
        else:
            comparable=("new_supply","new_supply_lower_bound","sales_units","absorption_rate","average_asp","metric_qualifiers")
            status="unchanged" if all(prior.get(f)==row.get(f) for f in comparable) else "conflict"
        decisions.append({"id":row["id"],"status":status,"period":row["period"],"source_id":row["source_id"]})
    generated=datetime.now(timezone.utc).isoformat()
    cand_payload={"schema_version":1,"generated_at":generated,"candidate_only":True,"record_count":len(candidate),"data":candidate}
    report={
      "schema_version":1,"generated_at":generated,"production_written":False,
      "configured_records":len(cfg.get("records",[])),
      "candidate_count":len(candidate),
      "validation_errors":errors,
      "counts":{
        "new":sum(x["status"]=="new" for x in decisions),
        "unchanged":sum(x["status"]=="unchanged" for x in decisions),
        "conflict":sum(x["status"]=="conflict" for x in decisions),
        "invalid":sum(x["status"]=="invalid" for x in decisions)
      },
      "decisions":decisions
    }
    dump(CAND,cand_payload)
    dump(ART,{"schema_version":1,"generated_at":generated,"candidate_only":True,"record_count":0,"data":[]})
    dump(REPORT,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if errors or report["counts"]["conflict"]:
        raise SystemExit("Historical backfill requires review")

if __name__=="__main__":
    main()
