"""Project listing coverage and source-access audit.

Scheduled checks do not invent asking prices when provider fetches return 403.
Status is written to a site-readable JSON and to a candidate audit artifact.
"""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LISTING = ROOT / "data/mock/market/listing-observations.json"
SCOPE = ROOT / "data/mock/market/listing-scope-evidence.json"
COLLECTOR = ROOT / "data/candidate/market/listing-collector-report.json"
OUTPUT = ROOT / "data/candidate/market/listing-coverage-backlog.json"
STATUS = ROOT / "data/state/listing-source-coverage.json"

def build(rows, collector, today, scoped_rows=None):
    groups = defaultdict(list)
    for row in rows:
        groups[row["project_id"]].append(row)
    scoped_by_project = defaultdict(list)
    for row in scoped_rows or []:
        scoped_by_project[row["project_id"]].append(row)
    collector_status = {x.get("project_id"): x for x in collector.get("projects", [])}
    details = []
    for pid, group in sorted(groups.items()):
        group.sort(key=lambda x: x.get("observation_date") or "")
        latest = group[-1]
        priced = (
            latest.get("coverage_status") == "full"
            and latest.get("asking_price_low_vnd_per_m2") is not None
            and latest.get("asking_price_high_vnd_per_m2") is not None
        )
        age = (today - date.fromisoformat(latest["observation_date"])).days
        fetched = collector_status.get(pid, {}).get("status", "not-checked")
        project_scopes = scoped_by_project.get(pid, [])
        # The alternative landed / apartment category is NOT project-level coverage.
        priority = 0 if not priced and not project_scopes else (
            1 if not priced else (2 if len({x["observation_date"] for x in group}) < 2 else 3)
        )
        details.append({
            "project_id": pid,
            "project_price_coverage": "full" if priced else "partial",
            "category_reference_count": len(project_scopes),
            "category_reference_scopes": sorted({x["price_scope"] for x in project_scopes}),
            "snapshot_count": len({x["observation_date"] for x in group}),
            "last_capture_date": latest["observation_date"],
            "days_since_capture": age,
            "collector_status": fetched,
            "priority": priority,
            "follow_up": (
                "review-project-aggregate-with-correct-product-class"
                if not priced and project_scopes else
                "find-category-correct-source"
                if not priced else
                "source-recheck-when-available"
            ),
        })
    details.sort(key=lambda x: (x["priority"], -x["days_since_capture"], x["project_id"]))
    raw_status = collector.get("source_access", "not-checked")
    return {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_access": raw_status,
        "source_checked_at": collector.get("generated_at"),
        "source_checks": collector.get("projects_checked", 0),
        "source_candidate_records": collector.get("candidate_records", 0),
        "projects_tracked": len(details),
        "aggregate_priced_projects": sum(x["project_price_coverage"] == "full" for x in details),
        "projects_with_2plus_snapshots": sum(x["snapshot_count"] >= 2 for x in details),
        "project_level_price_missing": sum(x["project_price_coverage"] == "partial" for x in details),
        "category_reference_projects": sum(x["category_reference_count"] > 0 for x in details),
        "category_reference_count": sum(x["category_reference_count"] for x in details),
        "no_new_price_inferred": True,
        "price_basis": "listing-asking-not-transactions",
        "source_note": "Blocked source: project price snapshots require independently reviewed publisher evidence. Category-only prices do not repair missing project-wide aggregate metrics.",
        "priority_backlog": details,
    }

def main():
    rows = json.loads(LISTING.read_text(encoding="utf-8"))["data"]
    scoped = json.loads(SCOPE.read_text(encoding="utf-8"))["data"]
    collector = json.loads(COLLECTOR.read_text(encoding="utf-8")) if COLLECTOR.exists() else {}
    payload = build(rows, collector, date.today(), scoped)
    for target in (OUTPUT, STATUS):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "priority_backlog"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
