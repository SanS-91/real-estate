from __future__ import annotations

from pathlib import Path
import argparse, copy, json
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
PROD_OBS=ROOT/"data/mock/market/observations.json"
PROD_ART=ROOT/"data/mock/articles/articles.json"
CAND_OBS=ROOT/"data/candidate/market/observations.json"
CAND_ART=ROOT/"data/candidate/market/articles.json"
REPORT=ROOT/"data/candidate/market/market-promotion-report.json"
SOURCES=ROOT/"data/mock/core/sources.json"
PROJECTS=ROOT/"data/mock/market/projects.json"

OBS_FIELDS=("new_supply","sales_units","absorption_rate","average_asp","asp_unit","currency","price_basis")
ART_FIELDS=("title","published_at","category","subcategory","content_type","region_ids","project_ids","developer_ids","tags","summary")

def read_json(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def write_json(path: Path, payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def obs_key(row):
    return (
        row.get("scope_type"),
        tuple(row.get("region_ids") or []),
        tuple(row.get("segment_ids") or []),
        row.get("period"),
        row.get("source_id"),
    )

def article_key(row):
    return (row.get("url"),row.get("source_id"))

def validate_observations(rows):
    sources={x["id"] for x in read_json(SOURCES,{"data":[]}).get("data",[])}
    problems=[]; seen=set()
    for i,row in enumerate(rows):
        key=obs_key(row)
        if not all([row.get("id"),row.get("scope_type"),row.get("period"),row.get("period_type"),row.get("source_id"),row.get("source_url")]):
            problems.append(f"observation row {i}: missing required identity/provenance field")
        if key in seen: problems.append(f"observation row {i}: duplicate candidate key {key}")
        seen.add(key)
        if row.get("source_id") not in sources:
            problems.append(f"observation row {i}: unknown source_id {row.get('source_id')}")
        if not row.get("region_ids") or not row.get("segment_ids"):
            problems.append(f"observation row {i}: region_ids and segment_ids are required")
        for field in ("new_supply","sales_units","average_asp"):
            value=row.get(field)
            if value is not None and (not isinstance(value,(int,float)) or value < 0):
                problems.append(f"observation row {i}: {field} must be non-negative number or null")
        ar=row.get("absorption_rate")
        if ar is not None and (not isinstance(ar,(int,float)) or ar < 0 or ar > 1):
            problems.append(f"observation row {i}: absorption_rate must be 0..1 or null")
    return problems

def validate_articles(rows):
    sources={x["id"] for x in read_json(SOURCES,{"data":[]}).get("data",[])}
    projects={x["id"] for x in read_json(PROJECTS,{"data":[]}).get("data",[])}
    problems=[]; seen=set()
    for i,row in enumerate(rows):
        key=article_key(row)
        if not all([row.get("id"),row.get("title"),row.get("url"),row.get("published_at"),row.get("source_id"),row.get("content_type")]):
            problems.append(f"article row {i}: missing required identity/provenance field")
        if key in seen: problems.append(f"article row {i}: duplicate candidate key {key}")
        seen.add(key)
        if row.get("source_id") not in sources:
            problems.append(f"article row {i}: unknown source_id {row.get('source_id')}")
        unknown=set(row.get("project_ids") or [])-projects
        if unknown:
            problems.append(f"article row {i}: unknown project_ids {sorted(unknown)}")
    return problems

def signature(row, fields):
    return tuple(json.dumps(row.get(f),ensure_ascii=False,sort_keys=True) for f in fields)

def classify(existing, candidates, key_fn, fields):
    by={key_fn(x):x for x in existing}
    decisions=[]
    for row in candidates:
        key=key_fn(row)
        prev=by.get(key)
        if prev is None:
            status="new"
        elif signature(prev,fields)==signature(row,fields):
            status="unchanged"
        else:
            status="conflict"
        changes={}
        if prev:
            for f in fields:
                if prev.get(f)!=row.get(f):
                    changes[f]={"from":prev.get(f),"to":row.get(f)}
        decisions.append({"id":row.get("id"),"key":list(key),"status":status,"changes":changes})
    return decisions

def promote_payload(existing_payload,candidates,decisions,key_fn,kind):
    if any(x["status"]=="conflict" for x in decisions):
        raise SystemExit(f"Refusing {kind} promotion: conflict detected")
    new_keys={tuple(x["key"]) for x in decisions if x["status"]=="new"}
    additions=[copy.deepcopy(x) for x in candidates if key_fn(x) in new_keys]
    out=copy.deepcopy(existing_payload)
    out["data"]=copy.deepcopy(existing_payload.get("data",[]))+additions
    if kind=="observations":
        out["data"].sort(key=lambda x:(x.get("scope_type") or "",x.get("period") or "",x.get("source_id") or "",x.get("id") or ""))
    else:
        out["data"].sort(key=lambda x:(x.get("published_at") or "",x.get("id") or ""),reverse=True)
    out["record_count"]=len(out["data"])
    out["build_id"]="phase5.5f2-market-promotion-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out["generated_at"]=datetime.now(timezone.utc).isoformat()
    return out,len(additions)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["preview","promote"],default="preview")
    ap.add_argument("--candidate-observations",default=str(CAND_OBS))
    ap.add_argument("--candidate-articles",default=str(CAND_ART))
    args=ap.parse_args()

    prod_obs=read_json(PROD_OBS,{"schema_version":1,"data":[]})
    prod_art=read_json(PROD_ART,{"schema_version":1,"data":[]})
    cand_obs=read_json(Path(args.candidate_observations),{"data":[]}).get("data",[])
    cand_art=read_json(Path(args.candidate_articles),{"data":[]}).get("data",[])

    errors=validate_observations(cand_obs)+validate_articles(cand_art)
    obs_decisions=classify(prod_obs.get("data",[]),cand_obs,obs_key,OBS_FIELDS) if not errors else []
    art_decisions=classify(prod_art.get("data",[]),cand_art,article_key,ART_FIELDS) if not errors else []
    report={
      "schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"mode":args.mode,
      "production_written":False,
      "candidate_observations":len(cand_obs),"candidate_articles":len(cand_art),
      "validation_errors":errors,
      "observation_decisions":obs_decisions,"article_decisions":art_decisions,
      "counts":{
        "observation_new":sum(x["status"]=="new" for x in obs_decisions),
        "observation_unchanged":sum(x["status"]=="unchanged" for x in obs_decisions),
        "observation_conflict":sum(x["status"]=="conflict" for x in obs_decisions),
        "article_new":sum(x["status"]=="new" for x in art_decisions),
        "article_unchanged":sum(x["status"]=="unchanged" for x in art_decisions),
        "article_conflict":sum(x["status"]=="conflict" for x in art_decisions),
      }
    }
    if errors:
        write_json(REPORT,report)
        raise SystemExit("\n".join(errors))

    if args.mode=="promote":
        if report["counts"]["observation_conflict"] or report["counts"]["article_conflict"]:
            write_json(REPORT,report)
            raise SystemExit("Refusing promotion: candidate conflicts with existing production")
        new_obs,added_obs=promote_payload(prod_obs,cand_obs,obs_decisions,obs_key,"observations")
        new_art,added_art=promote_payload(prod_art,cand_art,art_decisions,article_key,"articles")
        write_json(PROD_OBS,new_obs)
        write_json(PROD_ART,new_art)
        report["production_written"]=True
        report["added_observations"]=added_obs
        report["added_articles"]=added_art
        report["final_observations"]=new_obs["record_count"]
        report["final_articles"]=new_art["record_count"]

    write_json(REPORT,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
