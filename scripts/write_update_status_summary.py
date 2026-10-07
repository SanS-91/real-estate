#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

STATUS_ICON = {"healthy": "✅", "due": "🟡", "review": "🟡", "stale": "🔴"}

def clean(value):
    if value in (None, ""):
        return "—"
    return str(value).replace("|", "\\|")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = payload.get("datasets", [])

    counts = {"healthy": 0, "due": 0, "review": 0, "stale": 0}
    for row in rows:
        status = row.get("status", "review")
        counts[status] = counts.get(status, 0) + 1

    overall = payload.get("overall_status", "review")
    print("# Data Freshness Check")
    print()
    print(
        f"**Overall:** {STATUS_ICON.get(overall, '•')} `{overall}`  "
        f"· Healthy {counts.get('healthy', 0)}  "
        f"· Due/Review {counts.get('due', 0) + counts.get('review', 0)}  "
        f"· Stale {counts.get('stale', 0)}"
    )
    print()
    print(f"Generated: `{clean(payload.get('generated_at'))}`")
    print()
    print("| Module | Dataset | Status | Freshness | Latest period | Records | Last updated |")
    print("|---|---|---|---|---|---:|---|")
    for row in rows:
        status = row.get("status", "review")
        icon = STATUS_ICON.get(status, "•")
        print(
            f"| {clean(row.get('module'))} | {clean(row.get('label'))} "
            f"| {icon} {clean(status)} | {clean(row.get('freshness'))} "
            f"| {clean(row.get('latest_observation_period'))} "
            f"| {clean(row.get('record_count'))} | {clean(row.get('last_updated_at'))} |"
        )

    attention = [r for r in rows if r.get("status") in {"due", "review", "stale"}]
    print()
    if attention:
        print("## Needs attention")
        print()
        for row in attention:
            status = row.get("status", "review")
            print(
                f"- {STATUS_ICON.get(status, '•')} **{clean(row.get('label'))}** — "
                f"{clean(status)}; failure policy: `{clean(row.get('failure_behavior'))}`."
            )
    else:
        print("No dataset currently needs maintenance review.")
    print()
    print("> Read-only check: no external fetch, no promotion, no persistence, no repository commit.")

if __name__ == "__main__":
    main()
