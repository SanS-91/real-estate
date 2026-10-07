#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",default="data/state/market-coverage.json"); args=ap.parse_args()
    cfg=load(ROOT/"config/market_coverage_targets.json")
    projects=load(ROOT/"data/mock/market/projects.json")["data"]; devs=load(ROOT/"data/mock/core/developers.json")["data"]
    obs=load(ROOT/"data/mock/market/observations.json")["data"]; sources={x["id"]:x for x in load(ROOT/"data/mock/core/sources.json")["data"]}
    regions=Counter(); segments=Counter(); developers=Counter(); errors=[]
    for p in projects:
        for x in p.get("region_ids",[]): regions[x]+=1
        for x in p.get("segment_ids",[]): segments[x]+=1
        for x in p.get("developer_ids",[]): developers[x]+=1
        src=sources.get(p.get("primary_source_id"))
        if not src or src.get("source_type")!="developer": errors.append(f"{p['id']}: primary source is not first-party developer")
        if not str(p.get("official_url","")).startswith("http"): errors.append(f"{p['id']}: missing official URL")
        for k in ("average_asp","absorption_rate","sales_units","new_supply"):
            if k in p: errors.append(f"{p['id']}: observation field leaked into project master: {k}")
    first_party=sum(1 for p in projects if sources.get(p.get("primary_source_id"),{}).get("source_type")=="developer")
    share=round(first_party/len(projects),4) if projects else 0
    m=cfg["minimums"]
    checks={"projects":len(projects)>=m["projects"],"developers":len(devs)>=m["developers"],"first_party_project_share":share>=m["first_party_project_share"],"regions_with_projects":len(regions)>=m["regions_with_projects"],"segments_with_projects":len(segments)>=m["segments_with_projects"]}
    out={"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"mode":cfg["mode"],"status":"pass" if all(checks.values()) and not errors else "fail",
         "counts":{"projects":len(projects),"developers":len(devs),"observations":len(obs)},"first_party_project_share":share,
         "by_region":dict(sorted(regions.items())),"by_segment":dict(sorted(segments.items())),"by_developer":dict(sorted(developers.items())),"checks":checks,"errors":errors,
         "coverage_note":"Coverage can expand without inventing price, absorption, sales or supply metrics; quantitative gaps remain explicit."}
    dump(ROOT/args.output,out); print(f"Market coverage: {out['status']} · projects={len(projects)} · developers={len(devs)}")
    if out["status"]!="pass": raise SystemExit(1)
if __name__=="__main__": main()
