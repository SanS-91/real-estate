from __future__ import annotations

from pathlib import Path
import argparse
import copy
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "data/mock/market/listing-observations.json"
CANDIDATE = ROOT / "data/candidate/market/listing-observations.json"
REPORT = ROOT / "data/candidate/market/listing-refresh-report.json"
PROJECTS = ROOT / "data/mock/market/projects.json"

FIELDS = (
    "asking_price_low_vnd_per_m2",
    "asking_price_high_vnd_per_m2",
    "asking_price_change_1y_pct",
    "popular_area_low_sqm",
    "popular_area_high_sqm",
    "coverage_status",
)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def logical_key(row: dict):
    return (
        row.get("project_id"),
        row.get("asset_type"),
        row.get("source_id"),
        row.get("observation_date"),
    )


def series_key(row: dict):
    return (
        row.get("project_id"),
        row.get("asset_type"),
        row.get("source_id"),
    )


def comparable_signature(row: dict):
    return tuple(row.get(field) for field in FIELDS) + (
        json.dumps(row.get("product_price_ranges") or [], ensure_ascii=False, sort_keys=True),
        (row.get("volatile_metrics") or {}).get("listing_count"),
        (row.get("volatile_metrics") or {}).get("project_views_7d"),
    )


def validate(rows: list[dict]):
    project_ids = {x["id"] for x in read_json(PROJECTS, {"data":[]}).get("data", [])}
    problems = []
    seen = set()
    for i, row in enumerate(rows):
        key = logical_key(row)
        if not all(key):
            problems.append(f"row {i}: incomplete logical key {key}")
        if key in seen:
            problems.append(f"row {i}: duplicate logical key {key}")
        seen.add(key)
        if row.get("project_id") not in project_ids:
            problems.append(f"row {i}: unknown project_id {row.get('project_id')}")
        if row.get("market_layer") != "listing-asking":
            problems.append(f"row {i}: market_layer must be listing-asking")
        if row.get("source_id") != "batdongsan-com-vn":
            problems.append(f"row {i}: unsupported source_id {row.get('source_id')}")
        if row.get("coverage_status") not in {"full", "partial"}:
            problems.append(f"row {i}: coverage_status must be full or partial")
        if row.get("coverage_status") == "partial":
            lo, hi = row.get("asking_price_low_vnd_per_m2"), row.get("asking_price_high_vnd_per_m2")
            if (lo is None) != (hi is None):
                problems.append(f"row {i}: partial aggregate price must be both present or both blank")
    return problems


def latest_before(rows: list[dict], candidate: dict):
    matches = [
        x for x in rows
        if series_key(x) == series_key(candidate)
        and str(x.get("observation_date") or "") < str(candidate.get("observation_date") or "")
    ]
    return sorted(matches, key=lambda x: x.get("observation_date") or "")[-1] if matches else None


def classify(existing: list[dict], candidate_rows: list[dict]):
    existing_by_key = {logical_key(x): x for x in existing}
    decisions = []
    for row in candidate_rows:
        key = logical_key(row)
        exact = existing_by_key.get(key)
        previous = latest_before(existing, row)
        if exact:
            status = "unchanged" if comparable_signature(exact) == comparable_signature(row) else "conflict"
        elif previous is None:
            status = "new"
        elif comparable_signature(previous) == comparable_signature(row):
            status = "new-unchanged"
        else:
            status = "new-changed"

        change = {}
        if previous:
            for field in FIELDS:
                before, after = previous.get(field), row.get(field)
                if before != after:
                    change[field] = {"from": before, "to": after}
            prev_v = previous.get("volatile_metrics") or {}
            new_v = row.get("volatile_metrics") or {}
            for field in ("listing_count", "project_views_7d"):
                if prev_v.get(field) != new_v.get(field):
                    change[f"volatile_metrics.{field}"] = {"from": prev_v.get(field), "to": new_v.get(field)}

        decisions.append({
            "project_id": row.get("project_id"),
            "observation_date": row.get("observation_date"),
            "logical_key": list(key),
            "status": status,
            "previous_observation_date": previous.get("observation_date") if previous else None,
            "changes": change,
        })
    return decisions


def promote(existing_payload: dict, candidate_rows: list[dict], decisions: list[dict]):
    conflicts = [x for x in decisions if x["status"] == "conflict"]
    if conflicts:
        raise SystemExit(f"Refusing promotion: {len(conflicts)} conflict(s) on existing logical keys")

    incoming_keys = {
        tuple(x["logical_key"]) for x in decisions
        if x["status"] in {"new", "new-unchanged", "new-changed"}
    }
    additions = [copy.deepcopy(x) for x in candidate_rows if logical_key(x) in incoming_keys]

    final = [copy.deepcopy(x) for x in existing_payload.get("data", [])] + additions
    final.sort(key=lambda x: (x.get("project_id") or "", x.get("asset_type") or "", x.get("observation_date") or "", x.get("id") or ""))
    out = copy.deepcopy(existing_payload)
    out["schema_version"] = max(int(out.get("schema_version", 1)), 2)
    out["build_id"] = "phase5.5c-listing-history-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out["generated_at"] = datetime.now(timezone.utc).isoformat()
    out["record_count"] = len(final)
    out["data"] = final
    return out, len(additions)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preview", "promote"], default="preview")
    parser.add_argument("--candidate", default=str(CANDIDATE))
    args = parser.parse_args()

    existing_payload = read_json(PRODUCTION, {"schema_version":1, "data":[]})
    candidate_payload = read_json(Path(args.candidate), {"data":[]})
    candidate_rows = candidate_payload.get("data", [])

    problems = validate(candidate_rows)
    decisions = classify(existing_payload.get("data", []), candidate_rows) if not problems else []
    summary = {
        "mode": args.mode,
        "candidate_records": len(candidate_rows),
        "existing_records": len(existing_payload.get("data", [])),
        "validation_errors": problems,
        "decisions": decisions,
        "counts": {status: sum(1 for x in decisions if x["status"] == status) for status in ["new","new-unchanged","new-changed","unchanged","conflict"]},
    }

    if problems:
        write_json(REPORT, summary)
        raise SystemExit("\n".join(problems))

    if args.mode == "promote":
        promoted, added = promote(existing_payload, candidate_rows, decisions)
        write_json(PRODUCTION, promoted)
        summary["added"] = added
        summary["final_records"] = promoted["record_count"]

    write_json(REPORT, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
