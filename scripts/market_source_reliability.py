"""Phase 4H: track multi-run publisher reliability without publishing price data.

Consumes the 4G persisted access report. Rolling evidence distinguishes
reachable URLs from verifiable monthly prices; historical/listing references
cannot be counted as recurring project price coverage.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEALTH = ROOT / "data/state/alternative-source-health.json"
TARGETS = ROOT / "config/market-alternative-auto-targets.json"
OUTPUT = ROOT / "data/state/market-source-reliability.json"
WINDOW = 14
VALID_MONTHLY = {"candidate-staged", "same-period-unchanged", "new-period-candidate"}
UNVERIFIABLE = {"reachable-no-verifiable-metric", "challenge-or-access-wall"}
HISTORICAL = "historical-reference-monitor"


def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def classify(target, checks):
    mode = target["mode"]
    if mode != "monthly-price-candidate":
        return "historical-only" if mode == HISTORICAL else "listing-only"
    if not checks:
        return "not-yet-measured"
    statuses = [x["status"] for x in checks]
    successful = sum(status in VALID_MONTHLY for status in statuses)
    latest = statuses[-1]
    if latest in UNVERIFIABLE:
        return "needs-stable-alternative"
    if latest in VALID_MONTHLY and successful >= 2:
        return "repeatably-parseable"
    if latest in VALID_MONTHLY:
        return "source-parseable-not-yet-repeatable"
    return "not-verifiably-parseable"


def update(previous, targets, health, run_id, observed_at):
    old = {x["target_id"]: x for x in previous.get("targets", [])}
    current = {x["target_id"]: x for x in health.get("checks", [])}
    results = []
    for target in targets["targets"]:
        key = target["target_id"]
        past = list(old.get(key, {}).get("checks", []))
        fresh = current.get(key)
        if fresh is not None and not any(x.get("run_id") == run_id for x in past):
            past.append({
                "run_id": run_id,
                "observed_at": observed_at,
                "status": fresh.get("status", "missing-status"),
                "http_status": fresh.get("http_status"),
                "publisher_periods": fresh.get("parser_diagnostics", {}).get("publisher_periods", []),
            })
        past = past[-WINDOW:]
        results.append({
            "target_id": key,
            "source_id": target["source_id"],
            "project_id": target["project_id"],
            "mode": target["mode"],
            "price_metric": target["metric_type"],
            "checks": past,
            "check_count": len(past),
            "parseable_check_count": sum(x["status"] in VALID_MONTHLY for x in past),
            "classification": classify(target, past),
        })
    return {
        "schema_version": 1,
        "description": "Rolling publisher-source health only. This file never supplies price values or triggers promotion.",
        "window_runs": WINDOW,
        "targets": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    previous = load(OUTPUT, {})
    report = update(
        previous, load(TARGETS, {"targets": []}), load(HEALTH, {}),
        str(args.run_id), datetime.now(timezone.utc).isoformat()
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in report["targets"]:
        print(f"{row['target_id']}: {row['classification']} ({row['parseable_check_count']}/{row['check_count']} parseable)")
    print("Source reliability evaluated; no candidate or production price modified.")


if __name__ == "__main__":
    main()
