from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import json
import os
import shutil
import tempfile

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def logical_key(record: dict, fields: list[str]) -> tuple:
    values = tuple(record.get(f) for f in fields)
    if any(v in (None, "") for v in values):
        raise ValueError(f"Record {record.get('id')} missing logical key field(s): {fields}")
    return values


def semantic_payload(record: dict) -> dict:
    """Fields that define the canonical fact; fetch/promote timestamps are deliberately ignored."""
    keep = [
        "indicator_id", "period", "period_type", "data_date", "value", "unit",
        "source_id", "source_url", "published_at", "evidence_status",
        "methodology_note", "source_record_id", "observation_status"
    ]
    return {k: record.get(k) for k in keep}


def production_record(preview_record: dict, promoted_at: str, run_id: str) -> dict:
    out = dict(preview_record)
    out.pop("preview_only", None)
    out.pop("preview_promoted_at", None)
    out.pop("preview_reviewed_at", None)
    out["source_record_id"] = out.get("source_record_id") or out.get("id")
    out["observation_status"] = "final"
    out["promoted_at"] = promoted_at
    out["promotion_run_id"] = run_id
    return out


def prune_snapshots(snapshot_root: Path, max_snapshots: int):
    if not snapshot_root.exists() or max_snapshots <= 0:
        return
    dirs = sorted([p for p in snapshot_root.iterdir() if p.is_dir()], key=lambda p: p.name)
    while len(dirs) > max_snapshots:
        victim = dirs.pop(0)
        shutil.rmtree(victim, ignore_errors=True)


def build_production(preview_dir: Path, processed_dir: Path, policy_path: Path):
    policy = read_json(policy_path)
    if policy.get("mode") != "controlled-production-v1" or policy.get("production_write") is not True:
        raise ValueError("Safety violation: expected controlled-production-v1 with production_write=true")
    if policy.get("repository_publish") is not False or policy.get("frontend_publish") is not False:
        raise ValueError("Safety violation: Phase 4.2E must keep repository_publish=false and frontend_publish=false")

    canonical_payload = read_json(preview_dir / "canonical-observations.preview.json")
    manifest_payload = read_json(preview_dir / "promotion-manifest.json")
    preview_meta = read_json(preview_dir / "preview-meta.json")

    if canonical_payload.get("preview_only") is not True:
        raise ValueError("Safety violation: input canonical file is not a preview")
    if manifest_payload.get("production_write") is not False:
        raise ValueError("Safety violation: input promotion manifest must be dry-run only")

    run_id = str(preview_meta.get("source_run_id") or canonical_payload.get("source_run_id") or "unknown-run")
    promoted_at = now_iso()
    allowed_indicators = policy.get("allowed_indicators", {})
    allowed_readiness = set(policy.get("allowed_readiness_statuses", []))
    key_fields = list(policy.get("logical_key_fields", ["indicator_id", "period_type", "period"]))

    manifest_by_indicator = {r.get("indicator_id"): r for r in manifest_payload.get("data", [])}

    processed_path = processed_dir / "observations.json"
    if processed_path.exists():
        prior_payload = read_json(processed_path)
    else:
        prior_payload = {
            "schema_version": 1,
            "generated_at": None,
            "record_count": 0,
            "production_write": True,
            "repository_publish": False,
            "frontend_publish": False,
            "data": []
        }

    prior_records = prior_payload.get("data", [])
    if prior_payload.get("record_count", len(prior_records)) != len(prior_records):
        raise ValueError("Existing production record_count does not match data length")

    prior_index = {}
    prior_ids = set()
    for r in prior_records:
        rid = r.get("id")
        if not rid or rid in prior_ids:
            raise ValueError(f"Existing production contains missing/duplicate id: {rid}")
        prior_ids.add(rid)
        key = logical_key(r, key_fields)
        if key in prior_index:
            raise ValueError(f"Existing production duplicate logical key: {key}")
        prior_index[key] = r

    additions = []
    unchanged = []
    held = []
    conflicts = []

    for preview in canonical_payload.get("data", []):
        indicator_id = preview.get("indicator_id")
        m = manifest_by_indicator.get(indicator_id, {})
        cfg = allowed_indicators.get(indicator_id)

        if cfg is None:
            held.append({
                "indicator_id": indicator_id,
                "period": preview.get("period"),
                "action": "hold-not-allowlisted",
                "reason": "Indicator is outside Phase 4.2E production allowlist."
            })
            continue
        if m.get("readiness_status") not in allowed_readiness or m.get("action") != "promote-canonical-preview":
            held.append({
                "indicator_id": indicator_id,
                "period": preview.get("period"),
                "action": "hold-readiness",
                "reason": f"Readiness/action not allowed: {m.get('readiness_status')} / {m.get('action')}"
            })
            continue
        if preview.get("source_id") not in set(cfg.get("allowed_sources", [])):
            held.append({
                "indicator_id": indicator_id,
                "period": preview.get("period"),
                "action": "hold-source",
                "reason": f"Source {preview.get('source_id')} is not approved for {indicator_id}."
            })
            continue
        if preview.get("evidence_status") != cfg.get("required_evidence_status"):
            held.append({
                "indicator_id": indicator_id,
                "period": preview.get("period"),
                "action": "hold-evidence-status",
                "reason": f"Expected evidence_status={cfg.get('required_evidence_status')}."
            })
            continue
        if preview.get("period_type") != cfg.get("required_period_type"):
            held.append({
                "indicator_id": indicator_id,
                "period": preview.get("period"),
                "action": "hold-period-type",
                "reason": f"Expected period_type={cfg.get('required_period_type')}."
            })
            continue

        prod = production_record(preview, promoted_at, run_id)
        key = logical_key(prod, key_fields)
        old = prior_index.get(key)
        if old is None:
            additions.append(prod)
            continue

        if semantic_payload(old) == semantic_payload(prod):
            unchanged.append({
                "indicator_id": indicator_id,
                "period": prod.get("period"),
                "action": "unchanged",
                "existing_id": old.get("id"),
                "candidate_source_record_id": prod.get("source_record_id")
            })
        else:
            conflicts.append({
                "indicator_id": indicator_id,
                "period": prod.get("period"),
                "action": "conflict-blocked",
                "existing": semantic_payload(old),
                "incoming": semantic_payload(prod)
            })

    if conflicts:
        # Write a conflict report outside the canonical observations file and abort before mutation.
        processed_dir.mkdir(parents=True, exist_ok=True)
        write_json(processed_dir / "promotion-conflicts.json", {
            "schema_version": 1,
            "generated_at": promoted_at,
            "source_run_id": run_id,
            "record_count": len(conflicts),
            "data": conflicts
        })
        raise ValueError(f"Production promotion blocked by {len(conflicts)} historical conflict(s)")

    merged = list(prior_records) + additions
    merged.sort(key=lambda r: (r.get("indicator_id", ""), r.get("period") or "", r.get("id", "")))

    # Guardrail: merge-only v1 can never reduce production history.
    if len(merged) < len(prior_records):
        raise ValueError("Record-drop anomaly: merged production has fewer records than prior production")
    new_keys = {logical_key(r, key_fields) for r in merged}
    if not set(prior_index.keys()).issubset(new_keys):
        raise ValueError("Record-drop anomaly: one or more historical logical keys disappeared")

    processed_dir.mkdir(parents=True, exist_ok=True)
    snapshot_root = processed_dir / "_snapshots"
    snapshot_dir = snapshot_root / run_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    write_json(snapshot_dir / "observations.pre-promotion.json", prior_payload)
    write_json(snapshot_dir / "snapshot-meta.json", {
        "schema_version": 1,
        "created_at": promoted_at,
        "source_run_id": run_id,
        "prior_record_count": len(prior_records),
        "rollback_file": "observations.pre-promotion.json"
    })

    output_payload = {
        "schema_version": 1,
        "generated_at": promoted_at,
        "record_count": len(merged),
        "production_write": True,
        "repository_publish": False,
        "frontend_publish": False,
        "source_run_id": run_id,
        "data": merged
    }

    # Atomic replace of the canonical observations file.
    tmp_dir = Path(tempfile.mkdtemp(prefix="macro-production-", dir=str(processed_dir)))
    try:
        tmp_file = tmp_dir / "observations.json"
        write_json(tmp_file, output_payload)
        os.replace(tmp_file, processed_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    run_report = {
        "schema_version": 1,
        "generated_at": promoted_at,
        "mode": "controlled-production-v1",
        "production_write": True,
        "repository_publish": False,
        "frontend_publish": False,
        "source_run_id": run_id,
        "prior_record_count": len(prior_records),
        "added_record_count": len(additions),
        "unchanged_record_count": len(unchanged),
        "held_record_count": len(held),
        "conflict_count": 0,
        "final_record_count": len(merged),
        "snapshot_path": str(snapshot_dir.relative_to(ROOT)) if ROOT in snapshot_dir.parents else str(snapshot_dir),
        "added": [
            {
                "indicator_id": r.get("indicator_id"),
                "period": r.get("period"),
                "value": r.get("value"),
                "unit": r.get("unit"),
                "source_id": r.get("source_id"),
                "source_record_id": r.get("source_record_id")
            }
            for r in additions
        ],
        "unchanged": unchanged,
        "held": held,
        "notes": [
            "Production output exists only in the workflow workspace/cache and review artifact in Phase 4.2E.",
            "No git commit/push occurs and the frontend remains disconnected from data/processed."
        ]
    }
    write_json(processed_dir / "promotion-run.json", run_report)

    with (processed_dir / "promotion-summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["indicator_id", "period", "action", "value", "unit", "source_id", "reason"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in additions:
            w.writerow({
                "indicator_id": r.get("indicator_id"), "period": r.get("period"), "action": "added",
                "value": r.get("value"), "unit": r.get("unit"), "source_id": r.get("source_id"), "reason": ""
            })
        for r in unchanged:
            w.writerow({
                "indicator_id": r.get("indicator_id"), "period": r.get("period"), "action": "unchanged",
                "value": "", "unit": "", "source_id": "", "reason": "same canonical fact already exists"
            })
        for r in held:
            w.writerow({
                "indicator_id": r.get("indicator_id"), "period": r.get("period"), "action": r.get("action"),
                "value": "", "unit": "", "source_id": "", "reason": r.get("reason")
            })

    prune_snapshots(snapshot_root, int(policy.get("max_snapshots", 10)))
    # A prior conflict report must not survive a successful promotion and confuse reviewers.
    conflict_path = processed_dir / "promotion-conflicts.json"
    if conflict_path.exists():
        conflict_path.unlink()

    return output_payload, run_report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview-dir", default="data/staging/macro-preview")
    ap.add_argument("--processed-dir", default="data/processed/macro")
    ap.add_argument("--policy", default="config/production_promotion_policy.json")
    args = ap.parse_args()

    def resolve_arg(value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else ROOT / p

    preview_dir = resolve_arg(args.preview_dir)
    processed_dir = resolve_arg(args.processed_dir)
    policy_path = resolve_arg(args.policy)

    # Hard path guard: production writer may write only under data/processed/macro.
    resolved = processed_dir.resolve()
    allowed = (ROOT / "data/processed/macro").resolve()
    if resolved != allowed:
        raise SystemExit(f"Safety violation: production output must be exactly {allowed}")

    output, report = build_production(preview_dir, processed_dir, policy_path)
    print(json.dumps({"production": {"record_count": output["record_count"]}, "run": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
