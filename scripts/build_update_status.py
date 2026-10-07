#!/usr/bin/env python3
"""Build a lightweight update-status registry from existing datasets.

This script does not fetch the network and does not change production data.
It only summarizes the current repository state against config/update_matrix.json.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "config/update_matrix.json"
DEFAULT_OUTPUT = ROOT / "data/state/update-status.json"


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def max_text(values: list[str]) -> str | None:
    clean = [str(v) for v in values if v not in (None, "")]
    return max(clean) if clean else None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_payload(entry: dict[str, Any], as_of: datetime) -> dict[str, Any]:
    path = ROOT / entry["data_path"]
    payload = load_json(path)
    data = payload.get("data", [])
    if not isinstance(data, list):
        data = []

    selected = data
    indicator_ids = set(entry.get("indicator_ids", []))
    if indicator_ids:
        selected = [r for r in data if r.get("indicator_id") in indicator_ids]

    refresh_text = payload.get("generated_at") or payload.get("updated_at")
    refresh_dt = parse_dt(refresh_text)

    published = [r.get("published_at") for r in selected if r.get("published_at")]
    periods = [r.get("period") for r in selected if r.get("period")]
    updated = [r.get("updated_at") for r in selected if r.get("updated_at")]

    if not refresh_text and updated:
        refresh_text = max_text(updated)
        refresh_dt = parse_dt(refresh_text)

    stale_after = entry.get("stale_after_hours")
    age_hours = None
    if refresh_dt:
        age_hours = round((as_of.astimezone(timezone.utc) - refresh_dt.astimezone(timezone.utc)).total_seconds() / 3600, 1)

    if refresh_dt is None:
        freshness = "unknown"
        status = "review"
    elif stale_after is None:
        freshness = "current"
        status = "healthy"
    elif age_hours is not None and age_hours <= stale_after:
        freshness = "fresh"
        status = "healthy"
    elif age_hours is not None and age_hours <= stale_after * 1.25:
        freshness = "due"
        status = "due"
    else:
        freshness = "stale"
        status = "stale"

    return {
        "id": entry["id"],
        "module": entry["module"],
        "label": entry["label"],
        "update_mode": entry["update_mode"],
        "check_frequency": entry["check_frequency"],
        "update_trigger": entry["update_trigger"],
        "status": status,
        "freshness": freshness,
        "source_health": entry.get("source_health_mode", "unknown"),
        "last_checked_at": refresh_text,
        "last_updated_at": refresh_text,
        "latest_observation_period": max_text(periods),
        "latest_published_at": max_text(published),
        "record_count": len(selected),
        "age_hours": age_hours,
        "stale_after_hours": stale_after,
        "failure_behavior": entry.get("failure_behavior", "retain-last-good")
    }


def derived_payload(entry: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    dependencies = [by_id[d] for d in entry.get("depends_on", []) if d in by_id]
    states = [x["status"] for x in dependencies]
    if any(x == "stale" for x in states):
        status = "stale"
    elif any(x in {"due", "review"} for x in states):
        status = "due"
    else:
        status = "healthy"

    timestamps = [x.get("last_updated_at") for x in dependencies if x.get("last_updated_at")]
    return {
        "id": entry["id"],
        "module": entry["module"],
        "label": entry["label"],
        "update_mode": entry["update_mode"],
        "check_frequency": entry["check_frequency"],
        "update_trigger": entry["update_trigger"],
        "status": status,
        "freshness": "derived",
        "source_health": "derived",
        "last_checked_at": max_text(timestamps),
        "last_updated_at": max_text(timestamps),
        "latest_observation_period": None,
        "latest_published_at": None,
        "record_count": None,
        "age_hours": None,
        "stale_after_hours": None,
        "failure_behavior": entry.get("failure_behavior", "retain-last-good"),
        "depends_on": entry.get("depends_on", [])
    }


def build(matrix: dict[str, Any], as_of: datetime) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}

    for entry in matrix["datasets"]:
        if entry.get("data_path"):
            row = dataset_payload(entry, as_of)
            rows.append(row)
            by_id[row["id"]] = row

    for entry in matrix["datasets"]:
        if entry.get("depends_on"):
            row = derived_payload(entry, by_id)
            rows.append(row)
            by_id[row["id"]] = row

    overall = "healthy"
    if any(r["status"] == "stale" for r in rows):
        overall = "stale"
    elif any(r["status"] in {"due", "review"} for r in rows):
        overall = "due"

    return {
        "schema_version": 1,
        "generated_at": as_of.isoformat(),
        "timezone": matrix.get("timezone", "Asia/Ho_Chi_Minh"),
        "overall_status": overall,
        "dataset_count": len(rows),
        "principles": matrix.get("principles", {}),
        "datasets": rows
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--as-of", default=None, help="ISO-8601 timestamp for deterministic builds/tests")
    args = parser.parse_args()

    matrix = load_json(Path(args.matrix))
    as_of = parse_dt(args.as_of) if args.as_of else datetime.now().astimezone()
    if as_of is None:
        raise SystemExit("Invalid --as-of timestamp")

    result = build(matrix, as_of)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Update status written: {output}")
    print(f"Datasets: {result['dataset_count']} | Overall: {result['overall_status']}")


if __name__ == "__main__":
    main()
