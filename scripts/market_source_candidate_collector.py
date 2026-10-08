from __future__ import annotations

from pathlib import Path
import argparse
import importlib
import json
import re
from datetime import datetime, timezone
import requests

ROOT=Path(__file__).resolve().parents[1]
TARGETS=ROOT/"config/market-automation-targets.json"
PROD_OBS=ROOT/"data/mock/market/observations.json"
PROD_ART=ROOT/"data/mock/articles/articles.json"
CAND_OBS=ROOT/"data/candidate/market/observations.json"
CAND_ART=ROOT/"data/candidate/market/articles.json"
REPORT=ROOT/"data/candidate/market/market-source-candidate-report.json"
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; RealEstateMarketIntelligence/1.0; +https://github.com/SanS-91/real-estate)"}

def read_json(p, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

def write_json(p,payload):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def fetch(url):
    r=requests.get(url,headers=HEADERS,timeout=25,allow_redirects=True)
    return r.status_code,r.url,r.text

def slug(s):
    s=(s or "").lower()
    s=re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s[:80]

def existing_obs_key(x):
    return (x.get("scope_type"),tuple(x.get("region_ids") or []),tuple(x.get("segment_ids") or []),x.get("period"),x.get("source_id"))

def existing_article_key(x):
    return (x.get("url"),x.get("source_id"))

def build_cbre_rows(target, parsed, final_url):
    rows=[]
    for item in parsed:
        segment=item["segment_id"]
        rows.append({
            "id":f"obs-hcmc-{segment}-2026-q2-cbre",
            "scope_type":"region-segment",
            "region_ids":["hcmc"],
            "segment_ids":[segment],
            "period":"2026-Q2",
            "period_type":"quarter",
            "new_supply":item["new_supply"],
            "sales_units":None,
            "absorption_rate":None,
            "average_asp":None,
            "asp_unit":"vnd-per-m2" if segment=="apartment" else "vnd-per-m2-land",
            "currency":"VND",
            "price_basis":None,
            "source_id":target["observation_source_id"],
            "source_date":"2026-08-12",
            "source_url":final_url,
            "methodology_note":item["evidence_text"]+" Parsed automatically into candidate; requires review before promotion."
        })
    return rows

def project_regions(project_ids):
    projects=read_json(ROOT/"data/mock/market/projects.json",{"data":[]}).get("data",[])
    by={x.get("id"):x for x in projects}
    out=[]
    for pid in project_ids:
        row=by.get(pid,{})
        for key in ("region_id","region_ids"):
            val=row.get(key)
            if isinstance(val,str) and val not in out: out.append(val)
            elif isinstance(val,list):
                for v in val:
                    if v not in out: out.append(v)
    return out

def build_namlong_article(target, parsed, final_url):
    date=parsed.get("published_date") or target.get("period")
    project_ids=parsed.get("project_ids") or []
    tags=list(dict.fromkeys(parsed.get("tags") or []))
    summary_bits=[]
    for f in parsed.get("facts") or []:
        if f.get("type")=="developer-stated-sales":
            summary_bits.append(f"Developer states about {f.get('units',0):,} products with 100% absorption.")
        elif f.get("type")=="certificate-progress":
            summary_bits.append(f"Developer states {f.get('household_pct',0)*100:.0f}% of households received ownership certificates.")
    if not summary_bits:
        summary_bits.append("Nam Long official project update; structured project references extracted automatically for review.")
    return {
        "id":f"article-market-{slug(target['target_id'])}",
        "title":parsed.get("title") or "Nam Long official project update",
        "url":final_url,
        "category":"market",
        "subcategory":"developer",
        "content_type":"developer-update",
        "published_at":f"{date}T09:00:00+07:00" if date else None,
        "source_id":"nam-long-official",
        "region_ids":project_regions(project_ids),
        "project_ids":project_ids,
        "developer_ids":["nam-long"],
        "tags":tags,
        "importance":4 if len(project_ids)>=2 else 3,
        "summary":" ".join(summary_bits),
        "structured_facts":parsed.get("facts") or [],
        "candidate_note":"Automatically parsed from official developer page; review before production promotion."
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--target",action="append",default=[])
    args=ap.parse_args()
    cfg=read_json(TARGETS,{"targets":[]})
    selected=[x for x in cfg.get("targets",[]) if x.get("enabled") and x.get("collector") in {"cbre_market","namlong_official"}]
    if args.target:
        wanted=set(args.target)
        selected=[x for x in selected if x.get("target_id") in wanted]

    prod_obs=read_json(PROD_OBS,{"data":[]}).get("data",[])
    prod_art=read_json(PROD_ART,{"data":[]}).get("data",[])
    obs_by_key={existing_obs_key(x):x for x in prod_obs}
    art_keys={existing_article_key(x) for x in prod_art}

    obs_candidates=[]
    article_candidates=[]
    target_reports=[]

    for t in selected:
        try:
            status,final_url,html=fetch(t["url"])
            if status!=200:
                target_reports.append({"target_id":t["target_id"],"status":"http-error","http_status":status,"url":t["url"],"final_url":final_url})
                continue

            module=importlib.import_module("collectors."+t["collector"])
            if t["collector"]=="cbre_market":
                parsed=module.parse(html,final_url,datetime.now(timezone.utc).isoformat())
                built=build_cbre_rows(t,parsed,final_url)
                decisions=[]
                for row in built:
                    prev=obs_by_key.get(existing_obs_key(row))
                    if prev is None:
                        obs_candidates.append(row); state="new"
                    else:
                        material=("new_supply","sales_units","absorption_rate","average_asp","price_basis")
                        changed=any(prev.get(k)!=row.get(k) for k in material)
                        if changed:
                            obs_candidates.append(row); state="changed"
                        else:
                            state="unchanged"
                    decisions.append({"id":row["id"],"status":state,"segment":row["segment_ids"][0],"new_supply":row["new_supply"]})
                target_reports.append({"target_id":t["target_id"],"status":"parsed","type":"market-observation","records":len(built),"decisions":decisions})
            else:
                parsed=module.parse_article(html,final_url,datetime.now(timezone.utc).isoformat())
                row=build_namlong_article(t,parsed,final_url)
                key=existing_article_key(row)
                state="unchanged" if key in art_keys else "new"
                if state=="new":
                    article_candidates.append(row)
                target_reports.append({"target_id":t["target_id"],"status":"parsed","type":"developer-evidence","records":1,"decision":state,"project_ids":row["project_ids"]})
        except Exception as exc:
            target_reports.append({"target_id":t["target_id"],"status":"parse-error","error":f"{type(exc).__name__}: {exc}"[:400]})

    generated=datetime.now(timezone.utc).isoformat()
    obs_payload={"schema_version":1,"generated_at":generated,"candidate_only":True,"record_count":len(obs_candidates),"data":obs_candidates}
    art_payload={"schema_version":1,"generated_at":generated,"candidate_only":True,"record_count":len(article_candidates),"data":article_candidates}
    write_json(CAND_OBS,obs_payload)
    write_json(CAND_ART,art_payload)
    report={
        "schema_version":1,"generated_at":generated,"targets_checked":len(selected),
        "observation_candidates":len(obs_candidates),"article_candidates":len(article_candidates),
        "production_written":False,"targets":target_reports
    }
    write_json(REPORT,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
