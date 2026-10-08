#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/"config/history-coverage.json"
LISTING=ROOT/"data/mock/market/listing-observations.json"
MARKET=ROOT/"data/mock/market/observations.json"
LEGAL=ROOT/"data/mock/legal/documents.json"
INFRA=ROOT/"data/mock/infrastructure/schedules.json"
OUTPUT=ROOT/"data/state/history-coverage.json"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def uniq(values):
    return sorted({x for x in values if x not in (None,"")})

def listing_report(cfg,rows):
    threshold=int(cfg["rules"]["listing_market"]["trend_ready_snapshots"])
    by={}
    for row in rows:
        by.setdefault(row.get("project_id"),[]).append(row)
    items=[]
    for pid,group in sorted(by.items()):
        dates=uniq([x.get("observation_date") for x in group])
        items.append({
          "project_id":pid,
          "snapshot_count":len(dates),
          "first_snapshot":dates[0] if dates else None,
          "latest_snapshot":dates[-1] if dates else None,
          "trend_ready":len(dates)>=threshold,
          "missing_snapshots_to_trend_ready":max(0,threshold-len(dates))
        })
    return {
      "series_count":len(items),
      "trend_ready_series":sum(1 for x in items if x["trend_ready"]),
      "threshold_snapshots":threshold,
      "items":items
    }

def market_report(cfg,rows):
    threshold=int(cfg["rules"]["market_research"]["trend_ready_periods"])
    by={}
    for row in rows:
        if row.get("scope_type") not in {"region-segment","region-segment-benchmark"}:
            continue
        key=(
          row.get("scope_type"),
          tuple(row.get("region_ids") or []),
          tuple(row.get("segment_ids") or []),
          row.get("source_id")
        )
        by.setdefault(key,[]).append(row)
    items=[]
    for key,group in sorted(by.items(),key=lambda x:str(x[0])):
        periods=uniq([x.get("period") for x in group])
        items.append({
          "scope_type":key[0],
          "region_ids":list(key[1]),
          "segment_ids":list(key[2]),
          "source_id":key[3],
          "period_count":len(periods),
          "periods":periods,
          "trend_ready":len(periods)>=threshold,
          "missing_periods_to_trend_ready":max(0,threshold-len(periods))
        })
    return {
      "series_count":len(items),
      "trend_ready_series":sum(1 for x in items if x["trend_ready"]),
      "threshold_periods":threshold,
      "items":items
    }

def legal_report(cfg,rows):
    threshold=int(cfg["rules"]["legal"]["history_ready_years"])
    years=uniq([(x.get("issued_date") or x.get("effective_date") or "")[:4] for x in rows])
    relation_count=sum(len(x.get("related_documents") or []) for x in rows)
    return {
      "document_count":len(rows),
      "years":years,
      "year_count":len(years),
      "history_ready":len(years)>=threshold,
      "threshold_years":threshold,
      "relationship_count":relation_count
    }

def infrastructure_report(cfg,rows):
    threshold=int(cfg["rules"]["infrastructure"]["history_ready_schedule_records"])
    by={}
    for row in rows:
        by.setdefault(row.get("infrastructure_project_id"),[]).append(row)
    items=[]
    for pid,group in sorted(by.items()):
        ordered=sorted(group,key=lambda x:(x.get("announced_date") or "",x.get("id") or ""))
        items.append({
          "infrastructure_project_id":pid,
          "schedule_record_count":len(ordered),
          "history_ready":len(ordered)>=threshold,
          "current_records":sum(1 for x in ordered if x.get("status")=="current"),
          "superseded_records":sum(1 for x in ordered if x.get("status")=="superseded"),
          "first_announced_date":ordered[0].get("announced_date") if ordered else None,
          "latest_announced_date":ordered[-1].get("announced_date") if ordered else None
        })
    return {
      "series_count":len(items),
      "history_ready_series":sum(1 for x in items if x["history_ready"]),
      "threshold_schedule_records":threshold,
      "items":items
    }

def main():
    cfg=load(CFG)
    listing=listing_report(cfg,load(LISTING).get("data",[]))
    market=market_report(cfg,load(MARKET).get("data",[]))
    legal=legal_report(cfg,load(LEGAL).get("data",[]))
    infra=infrastructure_report(cfg,load(INFRA).get("data",[]))
    payload={
      "schema_version":1,
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "listing_market":listing,
      "market_research":market,
      "legal":legal,
      "infrastructure":infra,
      "principles":cfg.get("principles",[])
    }
    write(OUTPUT,payload)
    print(json.dumps({
      "listing_trend_ready":f"{listing['trend_ready_series']}/{listing['series_count']}",
      "market_trend_ready":f"{market['trend_ready_series']}/{market['series_count']}",
      "legal_history_ready":legal["history_ready"],
      "infrastructure_history_ready":f"{infra['history_ready_series']}/{infra['series_count']}"
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
