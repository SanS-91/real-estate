#!/usr/bin/env python3
"""Read-only source coverage summary for official registry candidate collectors.

Never exposes raw unreviewed candidates as production legal/infrastructure data.
"""
from __future__ import annotations
import argparse, json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODULES={
    "legal":{"canonical":"data/mock/legal/documents.json",
             "candidate_report":"data/candidate/legal/legal-candidate-report.json",
             "output":"data/state/legal-candidate-health.json"},
    "infrastructure":{"canonical":"data/mock/infrastructure/projects.json",
             "candidate_report":"data/candidate/infrastructure/infrastructure-candidate-report.json",
             "output":"data/state/infrastructure-candidate-health.json"},
}
WATCH="data/candidate/registry/watch-report.json"

def read(path):
    path=Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

def build(module,watch,report,canonical,now,job_status="success"):
    targets=[x for x in (watch or {}).get("targets",[]) if x.get("module")==module]
    discovery=[x for x in (watch or {}).get("discovery_links",[]) if x.get("module")==module]
    baseline=bool((watch or {}).get("previous_baseline_available"))
    errors=[x for x in (report or {}).get("results",[]) if x.get("status")=="fetch-error"]
    parsed=[x for x in (report or {}).get("results",[]) if x.get("status")=="parsed"]
    candidates=int((report or {}).get("candidate_count") or 0)
    if job_status!="success" or watch is None or report is None:
        state="incomplete"
    elif targets and all(not x.get("ok") for x in targets):
        state="source-unavailable"
    elif any(not x.get("ok") for x in targets) or errors:
        state="source-degraded"
    elif not baseline:
        state="baseline-initialized"
    elif candidates:
        state="candidates-await-review"
    else:
        state="checked-no-new-approved-data"
    return {
      "schema_version":1,"module":module,"generated_at":now,
      "status":state,"source_watch_at":(watch or {}).get("generated_at"),
      "candidate_report_at":(report or {}).get("generated_at"),
      "baseline_available":baseline,
      "canonical_record_count":len((canonical or {}).get("data",[])),
      "source_targets_checked":len(targets),
      "source_targets_reachable":sum(x.get("ok") is True for x in targets),
      "source_targets_failed":sum(x.get("ok") is not True for x in targets),
      "discovery_links_seen":len(discovery),
      "new_links_since_baseline":sum(x.get("new_since_previous_check") is True for x in discovery) if baseline else None,
      "candidate_detail_pages_parsed":len(parsed),
      "candidate_fetch_errors":len(errors),
      "candidates_awaiting_review_in_this_run":candidates if report is not None else None,
      "candidate_only":True,
      "production_written":False,
      "methodology":"Official-source URLs are monitored; new links and unreviewed candidates are not automatically published as legal acts or infrastructure milestones."
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--module",required=True,choices=MODULES)
    ap.add_argument("--watch",default=WATCH)
    ap.add_argument("--report")
    ap.add_argument("--output")
    ap.add_argument("--job-status",default="success")
    args=ap.parse_args()
    cfg=MODULES[args.module]
    out=ROOT/(args.output or cfg["output"])
    result=build(args.module,read(ROOT/args.watch),
                 read(ROOT/(args.report or cfg["candidate_report"])),
                 read(ROOT/cfg["canonical"]),datetime.now(timezone.utc).isoformat(),
                 args.job_status)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="methodology"},ensure_ascii=False))

if __name__=="__main__":
    main()
