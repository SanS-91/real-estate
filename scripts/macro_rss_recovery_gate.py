"""Recover missed Macro FX/gold checks after a successful RSS run.

A completed RSS run (whether GitHub- or Cloudflare-triggered) provides an
independent opportunity to verify the GitHub Macro workflow. No values are
promoted here; this gate can only dispatch the existing verified pipeline.
"""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def utc(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def eligible_slot(now):
    """Select the relevant scheduled Macro FX/gold check (UTC)."""
    now = now.astimezone(timezone.utc)
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    morning = base + timedelta(hours=3, minutes=15)
    afternoon = base + timedelta(hours=9, minutes=15)
    # Start checking after the normal RSS 11:20 or 17:20 ICT collection.
    if morning + timedelta(hours=1) <= now < morning + timedelta(hours=5, minutes=30):
        return morning
    if now.weekday() < 5 and afternoon + timedelta(hours=1) <= now < afternoon + timedelta(hours=5, minutes=30):
        return afternoon
    return None


def decide(now, runs):
    slot = eligible_slot(now)
    if slot is None:
        return False, "outside-macro-recovery-window", None
    eligible = []
    for run in runs:
        created = utc(run.get("createdAt") or run.get("created_at"))
        if (created is None or created < slot or created > now
                or run.get("event") not in ("schedule", "workflow_dispatch")):
            continue
        eligible.append(run)
    active = {"queued", "waiting", "pending", "in_progress", "requested"}
    if any(run.get("status") in active for run in eligible):
        return False, "macro-queued-or-running", slot
    if any(run.get("conclusion") == "success" for run in eligible):
        return False, "macro-already-success", slot
    return True, "macro-missed-or-failed", slot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-json", required=True)
    parser.add_argument("--now", help="Test-only ISO UTC time override")
    args = parser.parse_args()
    runs = json.loads(Path(args.runs_json).read_text(encoding="utf-8"))
    if not isinstance(runs, list):
        raise SystemExit("Macro run listing must be an array")
    now = utc(args.now) if args.now else datetime.now(timezone.utc)
    if not now:
        raise SystemExit("Invalid current time")
    needed, reason, slot = decide(now, runs)
    print(f"Macro recovery after RSS: dispatch={needed}, reason={reason}, slot={slot}")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"dispatch={str(needed).lower()}\n")
            stream.write(f"reason={reason}\n")
            if slot:
                stream.write(f"slot={slot.isoformat()}\n")


if __name__ == "__main__":
    main()
