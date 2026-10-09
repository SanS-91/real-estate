"""Coverage-first listing collector audit. Never turns a failed fetch into a price."""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LISTING=ROOT/"data/mock/market/listing-observations.json"
COLLECTOR=ROOT/"data/candidate/market/listing-collector-report.json"
OUTPUT=ROOT/"data/candidate/market/listing-coverage-backlog.json"
def build(rows,collector,today):
    groups=defaultdict(list)
    for row in rows:
        groups[row["project_id"]].append(row)
    status={x.get("project_id"):x for x in collector.get("projects",[])}
    details=[]
    for pid,group in sorted(groups.items()):
        group.sort(key=lambda x:x.get("observation_date") or "")
        latest=group[-1]
        priced=latest.get("coverage_status")=="full" and latest.get("asking_price_low_vnd_per_m2") is not None and latest.get("asking_price_high_vnd_per_m2") is not None
        last=date.fromisoformat(latest["observation_date"])
        age=(today-last).days
        fetched=status.get(pid,{}).get("status","not-checked")
        # Prioritize unpriced projects, then one-snapshot price series.
        priority=0 if not priced else (1 if len({x["observation_date"] for x in group})<2 else 2)
        details.append({
          "project_id":pid,
          "project_price_coverage":"full" if priced else "partial",
          "snapshot_count":len({x["observation_date"] for x in group}),
          "last_capture_date":latest["observation_date"],
          "days_since_capture":age,
          "collector_status":fetched,
          "priority":priority,
          "follow_up":"source-assisted-review" if fetched in ("http-error","fetch-error","degraded-no-range") or not priced else "source-recheck-when-available",
        })
    details.sort(key=lambda x:(x["priority"],-x["days_since_capture"],x["project_id"]))
    return {
      "schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),
      "source_access":collector.get("source_access","unknown"),
      "projects_tracked":len(details),
      "aggregate_priced_projects":sum(x["project_price_coverage"]=="full" for x in details),
      "projects_with_2plus_snapshots":sum(x["snapshot_count"]>=2 for x in details),
      "project_level_price_missing":sum(x["project_price_coverage"]=="partial" for x in details),
      "no_new_price_inferred":True,
      "priority_backlog":details,
    }
def main():
    rows=json.loads(LISTING.read_text(encoding="utf-8"))["data"]
    collector=json.loads(COLLECTOR.read_text(encoding="utf-8")) if COLLECTOR.exists() else {}
    payload=build(rows,collector,date.today())
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in payload.items() if k not in ("priority_backlog",)},ensure_ascii=False))
if __name__=="__main__":
    main()
