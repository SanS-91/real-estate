"""Fail-closed freshness gate for Market source candidates.

A successful HTTP request is not evidence of a new reporting period.
Existing Q2/2026 collectors contain fixed dates and period labels.
This gate prevents their outputs being presented as auto-verified updates.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ROOT / "config/market-automation-targets.json"
REPORT = ROOT / "data/candidate/market/market-source-candidate-report.json"
OUTPUT = ROOT / "data/candidate/market/market-freshness-report.json"

def evaluate(targets, report):
    by_id = {t["target_id"]: t for t in targets.get("targets", [])}
    results = []
    for item in report.get("targets", []):
        target = by_id.get(item.get("target_id"), {})
        # Explicitly require future collectors to provide a verified source period
        # and evidence URL, rather than trusting configuration period or fetch time.
        source_period = item.get("verified_source_period") or item.get("detected_period")
        source_date = item.get("verified_source_date")
        expected = target.get("period")
        passed = bool(
            item.get("status") == "parsed"
            and source_period and source_date
            and source_period == expected
            and item.get("source_period_evidence_url")
        )
        results.append({
            "target_id": item.get("target_id"),
            "configured_period": expected,
            "verified_source_period": source_period,
            "verified_source_date": source_date,
            "decision": "freshness-verified" if passed else "manual-review-required",
            "reason": "Source period/date evidence not independently verified" if not passed else "Source period verified against configured target",
        })
    return {"schema_version": 1, "auto_publish_eligible": False,
            "reason": "Auto-publish remains disabled pending end-to-end tests and approval",
            "targets": results}

def main():
    targets = json.loads(TARGETS.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    result = evaluate(targets, report)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
