#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--watch",default="data/candidate/registry/watch-report.json")
    ap.add_argument("--output",default="data/candidate/registry/review-queue.json")
    args=ap.parse_args()
    report=load(ROOT/args.watch); q=[]
    for x in report.get("targets",[]):
        if not x.get("ok"):
            q.append({"type":"source-health","module":x["module"],"entity_id":x["entity_id"],"url":x["url"],"priority":"high","reason":x.get("error") or f"HTTP {x.get('status_code')}"})
        elif x.get("changed_since_previous_check") and not x.get("discovery"):
            q.append({"type":"source-content-change","module":x["module"],"entity_id":x["entity_id"],"url":x["url"],"priority":"medium","reason":"Source fingerprint changed; review canonical facts before any update."})
    for x in report.get("discovery_links",[]):
        if x.get("new_since_previous_check"):
            q.append({"type":"discovery-link","module":x["module"],"entity_id":None,"url":x["url"],"title":x["title"],"priority":"medium","reason":"New keyword-matched official-source link; review required."})
    out={"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"mode":"assisted-review-queue-v1","auto_publish":False,"item_count":len(q),"items":q,
         "principles":["No candidate signal mutates Legal or Infrastructure registries.","Schedule changes are appended and prior current targets are superseded, never overwritten.","Insufficient evidence stays in review queue."]}
    dump(ROOT/args.output,out); print(f"Registry review queue: {len(q)} item(s)")
if __name__=="__main__": main()
