from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
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


def atomic_write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="repo-persist-", dir=str(path.parent)))
    try:
        tmp = temp_root / path.name
        write_json(tmp, payload)
        os.replace(tmp, path)
    finally:
        try:
            temp_root.rmdir()
        except OSError:
            pass


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def logical_key(record: dict, fields: list[str]) -> tuple:
    values = tuple(record.get(f) for f in fields)
    if any(v in (None, "") for v in values):
        raise ValueError(f"Record {record.get('id')} missing logical key field(s): {fields}")
    return values


def indexed(records: list[dict], key_fields: list[str]) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    ids: set[str] = set()
    for r in records:
        rid = r.get("id")
        if not rid or rid in ids:
            raise ValueError(f"Missing/duplicate record id: {rid}")
        ids.add(rid)
        key = logical_key(r, key_fields)
        if key in out:
            raise ValueError(f"Duplicate logical key: {key}")
        out[key] = r
    return out


def build_repository_persistence(
    incoming_dir: Path,
    repo_processed_dir: Path,
    report_dir: Path,
    source_run_number: int,
    source_run_database_id: str,
    persistence_policy_path: Path,
    promotion_policy_path: Path,
):
    policy = read_json(persistence_policy_path)
    production_policy = read_json(promotion_policy_path)
    if policy.get("mode") != "controlled-repository-persistence-v1" or policy.get("manual_only") is not True:
        raise ValueError("Safety violation: invalid repository persistence policy")
    if policy.get("repository_publish") is not True or policy.get("frontend_publish") is not False:
        raise ValueError("Safety violation: Phase 4.2F must publish only to repository, never frontend")

    incoming_obs_path = incoming_dir / "observations.json"
    incoming_run_path = incoming_dir / "promotion-run.json"
    if not incoming_obs_path.exists() or not incoming_run_path.exists():
        raise ValueError("Incoming macro-production artifact is missing observations.json or promotion-run.json")

    incoming = read_json(incoming_obs_path)
    promotion_run = read_json(incoming_run_path)
    incoming_records = incoming.get("data", [])
    if incoming.get("record_count") != len(incoming_records):
        raise ValueError("Incoming observations record_count mismatch")
    if incoming.get("production_write") is not True:
        raise ValueError("Incoming artifact is not a controlled production output")
    if incoming.get("repository_publish") is not policy.get("expected_source_repository_publish"):
        raise ValueError("Incoming artifact repository_publish flag is not the expected pre-persistence value")
    if incoming.get("frontend_publish") is not False:
        raise ValueError("Incoming artifact unexpectedly enables frontend publishing")
    if promotion_run.get("mode") != policy.get("allowed_source_production_mode"):
        raise ValueError("Incoming promotion-run mode is not allowed")
    if promotion_run.get("conflict_count") != 0:
        raise ValueError("Incoming promotion-run contains conflicts")
    if promotion_run.get("final_record_count") != len(incoming_records):
        raise ValueError("Incoming promotion-run final_record_count mismatch")
    if promotion_run.get("source_run_id") != incoming.get("source_run_id"):
        raise ValueError("Incoming promotion-run source_run_id does not match observations.json")

    key_fields = list(policy.get("logical_key_fields", ["indicator_id", "period_type", "period"]))
    incoming_index = indexed(incoming_records, key_fields)

    # Defense in depth: repository persistence repeats the core allowlist checks even
    # though validate_production.py runs immediately before this script in the workflow.
    allowed = production_policy.get("allowed_indicators", {})
    for r in incoming_records:
        cfg = allowed.get(r.get("indicator_id"))
        if not cfg:
            raise ValueError(f"Incoming indicator is not production-allowlisted: {r.get('indicator_id')}")
        if r.get("source_id") not in cfg.get("allowed_sources", []):
            raise ValueError(f"Incoming source is not production-allowlisted: {r.get('source_id')}")
        if r.get("evidence_status") != cfg.get("required_evidence_status"):
            raise ValueError(f"Incoming evidence status mismatch for {r.get('indicator_id')}")
        if r.get("period_type") != cfg.get("required_period_type"):
            raise ValueError(f"Incoming period type mismatch for {r.get('indicator_id')}")
        if r.get("observation_status") != "final":
            raise ValueError(f"Incoming record is not final: {r.get('id')}")
        if any(k.startswith("preview_") for k in r) or "preview_only" in r:
            raise ValueError(f"Preview-only field leaked into incoming production record: {r.get('id')}")

    repo_obs_path = repo_processed_dir / "observations.json"
    repo_meta_path = repo_processed_dir / "repository-publish.json"
    if repo_obs_path.exists():
        current = read_json(repo_obs_path)
        current_records = current.get("data", [])
        if current.get("record_count") != len(current_records):
            raise ValueError("Repository observations record_count mismatch")
        if current.get("repository_publish") is not True:
            raise ValueError("Existing repository production file is not marked repository_publish=true")
    else:
        current = {
            "schema_version": 1,
            "generated_at": None,
            "record_count": 0,
            "production_write": True,
            "repository_publish": True,
            "frontend_publish": False,
            "data": [],
        }
        current_records = []

    current_index = indexed(current_records, key_fields)
    current_meta = read_json(repo_meta_path) if repo_meta_path.exists() else None
    last_run_number = int(current_meta.get("source_run_number")) if current_meta and current_meta.get("source_run_number") is not None else None

    if last_run_number is not None and source_run_number < last_run_number:
        raise ValueError(
            f"Source run #{source_run_number} is older than last persisted run #{last_run_number}; older artifacts cannot move repository state backward"
        )

    # If the canonical records are exactly identical, persistence is intentionally a no-op.
    # This avoids a new git commit every day when the collector sees no new official data.
    exact_same = len(current_records) == len(incoming_records) and current_index == incoming_index
    published_at = now_iso()
    if exact_same:
        report = {
            "schema_version": 1,
            "generated_at": published_at,
            "mode": policy["mode"],
            "status": "no-change",
            "repository_write": False,
            "git_commit_expected": False,
            "frontend_publish": False,
            "source_run_number": source_run_number,
            "source_run_database_id": str(source_run_database_id),
            "source_artifact": f"{policy.get('source_artifact_prefix', 'macro-production-')}{source_run_number}",
            "source_promotion_run_id": incoming.get("source_run_id"),
            "prior_record_count": len(current_records),
            "added_record_count": 0,
            "final_record_count": len(incoming_records),
            "observations_sha256": file_sha256(incoming_obs_path),
            "notes": ["Incoming canonical records are identical to repository state; no repository files were rewritten."],
        }
        write_report(report_dir, report, [])
        return report

    # Any changing persistence must be based on exactly the repository record count
    # seen by the source controlled-production run. This prevents approving an artifact
    # produced from a stale repository baseline.
    if policy.get("require_prior_count_match_for_changes", True):
        reported_prior = promotion_run.get("prior_record_count")
        if reported_prior != len(current_records):
            raise ValueError(
                f"Stale production artifact: promotion-run prior_record_count={reported_prior}, repository currently has {len(current_records)}"
            )

    if last_run_number is not None and policy.get("require_monotonic_source_run_number", True) and source_run_number <= last_run_number:
        raise ValueError(
            f"Changing persistence requires a newer source run number than #{last_run_number}; got #{source_run_number}"
        )

    additions = []
    for key, old in current_index.items():
        incoming_old = incoming_index.get(key)
        if incoming_old is None:
            raise ValueError(f"Record-drop blocked: repository logical key disappeared from incoming artifact: {key}")
        if incoming_old != old:
            raise ValueError(f"Historical mutation blocked for repository logical key: {key}")
    for key, r in incoming_index.items():
        if key not in current_index:
            additions.append(r)

    if len(incoming_records) < len(current_records):
        raise ValueError("Record-drop blocked: incoming artifact has fewer records than repository")
    if not additions:
        raise ValueError("Repository state differs from incoming artifact but no append-only additions were identified")

    output = deepcopy(incoming)
    output["repository_publish"] = True
    output["frontend_publish"] = False
    output["repository_published_at"] = published_at
    output["repository_source_run_number"] = source_run_number
    output["repository_source_run_database_id"] = str(source_run_database_id)
    output["repository_persistence_mode"] = policy["mode"]

    repo_meta = {
        "schema_version": 1,
        "generated_at": published_at,
        "mode": policy["mode"],
        "repository_publish": True,
        "frontend_publish": False,
        "source_workflow": policy.get("source_workflow"),
        "source_run_number": source_run_number,
        "source_run_database_id": str(source_run_database_id),
        "source_artifact": f"{policy.get('source_artifact_prefix', 'macro-production-')}{source_run_number}",
        "source_promotion_run_id": incoming.get("source_run_id"),
        "source_generated_at": incoming.get("generated_at"),
        "prior_record_count": len(current_records),
        "added_record_count": len(additions),
        "final_record_count": len(incoming_records),
        "observations_sha256": None,
        "rollback": "Use git history/revert for repository-level rollback. Workflow-only production snapshots are intentionally not committed.",
    }

    atomic_write_json(repo_obs_path, output)
    repo_meta["observations_sha256"] = file_sha256(repo_obs_path)
    atomic_write_json(repo_meta_path, repo_meta)

    report = {
        "schema_version": 1,
        "generated_at": published_at,
        "mode": policy["mode"],
        "status": "ready-to-commit",
        "repository_write": True,
        "git_commit_expected": True,
        "frontend_publish": False,
        "source_run_number": source_run_number,
        "source_run_database_id": str(source_run_database_id),
        "source_artifact": repo_meta["source_artifact"],
        "source_promotion_run_id": incoming.get("source_run_id"),
        "prior_record_count": len(current_records),
        "added_record_count": len(additions),
        "final_record_count": len(incoming_records),
        "observations_sha256": repo_meta["observations_sha256"],
        "added": [
            {
                "indicator_id": r.get("indicator_id"),
                "period": r.get("period"),
                "value": r.get("value"),
                "unit": r.get("unit"),
                "source_id": r.get("source_id"),
                "id": r.get("id"),
            }
            for r in additions
        ],
        "notes": [
            "Repository files were prepared for an explicit git commit by the manual persistence workflow.",
            "Frontend publishing remains disabled in Phase 4.2F.",
        ],
    }
    write_report(report_dir, report, additions)
    return report


def write_report(report_dir: Path, report: dict, additions: list[dict]):
    report_dir.mkdir(parents=True, exist_ok=True)
    write_json(report_dir / "persistence-run.json", report)
    with (report_dir / "persistence-summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["indicator_id", "period", "action", "value", "unit", "source_id"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in additions:
            w.writerow({
                "indicator_id": r.get("indicator_id"),
                "period": r.get("period"),
                "action": "repository-add",
                "value": r.get("value"),
                "unit": r.get("unit"),
                "source_id": r.get("source_id"),
            })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--incoming-dir", required=True)
    ap.add_argument("--repo-processed-dir", default="data/processed/macro")
    ap.add_argument("--report-dir", default="data/staging/repository-persistence")
    ap.add_argument("--source-run-number", required=True, type=int)
    ap.add_argument("--source-run-database-id", required=True)
    ap.add_argument("--policy", default="config/repository_persistence_policy.json")
    ap.add_argument("--production-policy", default="config/production_promotion_policy.json")
    args = ap.parse_args()

    def resolve(value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else ROOT / p

    incoming_dir = resolve(args.incoming_dir)
    repo_processed_dir = resolve(args.repo_processed_dir)
    report_dir = resolve(args.report_dir)
    policy_path = resolve(args.policy)
    production_policy_path = resolve(args.production_policy)

    allowed_repo = (ROOT / "data/processed/macro").resolve()
    if repo_processed_dir.resolve() != allowed_repo:
        raise SystemExit(f"Safety violation: repository persistence target must be exactly {allowed_repo}")
    allowed_report_root = (ROOT / "data/staging/repository-persistence").resolve()
    if report_dir.resolve() != allowed_report_root:
        raise SystemExit(f"Safety violation: persistence report target must be exactly {allowed_report_root}")

    report = build_repository_persistence(
        incoming_dir,
        repo_processed_dir,
        report_dir,
        args.source_run_number,
        args.source_run_database_id,
        policy_path,
        production_policy_path,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
