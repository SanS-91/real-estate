from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import os
import tempfile

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def atomic_write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="daily-persist-", dir=str(path.parent)))
    try:
        tmp = temp_root / path.name
        write_json(tmp, payload)
        os.replace(tmp, path)
    finally:
        try:
            temp_root.rmdir()
        except OSError:
            pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def logical_key(record: dict, fields: list[str]) -> tuple:
    values = tuple(record.get(k) for k in fields)
    if any(v in (None, "") for v in values):
        raise ValueError(f"Missing logical-key field for record {record.get('id')}: {fields}")
    return values


def make_index(records: list[dict], key_fields: list[str]) -> dict[tuple, dict]:
    result: dict[tuple, dict] = {}
    ids: set[str] = set()
    for record in records:
        rid = record.get("id")
        if not rid or rid in ids:
            raise ValueError(f"Missing/duplicate record id: {rid}")
        ids.add(rid)
        key = logical_key(record, key_fields)
        if key in result:
            raise ValueError(f"Duplicate logical key: {key}")
        result[key] = record
    return result


def parse_day(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception as exc:
        raise ValueError(f"Daily auto-publish requires YYYY-MM-DD period; got {value!r}") from exc


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_daily_persistence(
    incoming_dir: Path,
    repo_processed_dir: Path,
    report_dir: Path,
    source_run_number: int,
    source_run_database_id: str,
    auto_policy_path: Path,
    daily_gate_path: Path,
    as_of: datetime | None = None,
):
    auto_policy = read_json(auto_policy_path)
    daily_gate = read_json(daily_gate_path)

    if auto_policy.get("mode") != "controlled-daily-auto-persistence-v1":
        raise ValueError("Safety violation: invalid daily auto-persistence policy")
    if auto_policy.get("repository_publish") is not True or auto_policy.get("frontend_publish") is not False:
        raise ValueError("Safety violation: daily policy must publish repository only")
    if daily_gate.get("mode") != "controlled-production-v1" or daily_gate.get("production_write") is not True:
        raise ValueError("Safety violation: invalid daily controlled-production gate")

    incoming_path = incoming_dir / "observations.json"
    incoming_run_path = incoming_dir / "promotion-run.json"
    if not incoming_path.exists() or not incoming_run_path.exists():
        raise ValueError("Incoming daily production artifact is incomplete")

    incoming = read_json(incoming_path)
    promotion_run = read_json(incoming_run_path)
    incoming_records = incoming.get("data", [])
    if incoming.get("record_count") != len(incoming_records):
        raise ValueError("Incoming record_count mismatch")
    if incoming.get("production_write") is not True or incoming.get("repository_publish") is not False:
        raise ValueError("Incoming file is not pre-persistence controlled production")
    if incoming.get("frontend_publish") is not False:
        raise ValueError("Incoming production unexpectedly enables frontend publishing")
    if promotion_run.get("mode") != "controlled-production-v1" or promotion_run.get("conflict_count") != 0:
        raise ValueError("Incoming production run is not conflict-free controlled production")
    if promotion_run.get("final_record_count") != len(incoming_records):
        raise ValueError("Incoming promotion-run final_record_count mismatch")
    if promotion_run.get("source_run_id") != incoming.get("source_run_id"):
        raise ValueError("Incoming promotion run id mismatch")

    repo_obs_path = repo_processed_dir / "observations.json"
    repo_meta_path = repo_processed_dir / "repository-publish.json"
    current = read_json(repo_obs_path)
    current_records = current.get("data", [])
    if current.get("record_count") != len(current_records):
        raise ValueError("Repository record_count mismatch")
    if current.get("repository_publish") is not True:
        raise ValueError("Current repository observations are not canonical repository data")

    key_fields = list(auto_policy.get("logical_key_fields", ["indicator_id", "period_type", "period"]))
    current_index = make_index(current_records, key_fields)
    incoming_index = make_index(incoming_records, key_fields)

    if auto_policy.get("require_prior_count_match", True):
        if promotion_run.get("prior_record_count") != len(current_records):
            raise ValueError(
                f"Stale baseline blocked: production prior_record_count={promotion_run.get('prior_record_count')}, "
                f"repository count={len(current_records)}"
            )

    for key, old in current_index.items():
        new = incoming_index.get(key)
        if new is None:
            raise ValueError(f"Record-drop blocked: {key}")
        if new != old:
            raise ValueError(f"Historical mutation blocked: {key}")

    additions = [record for key, record in incoming_index.items() if key not in current_index]
    if not additions:
        report = {
            "schema_version": 1,
            "generated_at": now_iso(),
            "mode": auto_policy["mode"],
            "status": "no-change",
            "repository_write": False,
            "git_commit_expected": False,
            "source_run_number": source_run_number,
            "source_run_database_id": str(source_run_database_id),
            "prior_record_count": len(current_records),
            "added_record_count": 0,
            "final_record_count": len(current_records),
            "notes": ["No new corroborated daily FX/gold fact; repository remains unchanged."],
        }
        write_json(report_dir / "daily-auto-persistence.json", report)
        return report

    max_additions = int(auto_policy.get("max_additions_per_run", 3))
    if len(additions) > max_additions:
        raise ValueError(f"Safety stop: {len(additions)} additions exceed max {max_additions}")

    allowed_ids = set(auto_policy.get("allowed_indicator_ids", []))
    gate_allowed = daily_gate.get("allowed_indicators", {})
    local_tz = ZoneInfo(auto_policy.get("timezone", "Asia/Ho_Chi_Minh"))
    local_now = as_of.astimezone(local_tz) if as_of else datetime.now(local_tz)
    today = local_now.date()
    max_age_days = int(auto_policy.get("max_period_age_days", 4))

    latest_by_indicator: dict[str, date] = {}
    for record in current_records:
        iid = record.get("indicator_id")
        if iid in allowed_ids and record.get("period_type") == "day":
            p = parse_day(record.get("period"))
            latest_by_indicator[iid] = max(latest_by_indicator.get(iid, p), p)

    for record in additions:
        iid = record.get("indicator_id")
        if iid not in allowed_ids or iid not in gate_allowed:
            raise ValueError(f"Non-daily indicator blocked from auto-persistence: {iid}")
        cfg = gate_allowed[iid]
        if record.get("period_type") != cfg.get("required_period_type"):
            raise ValueError(f"Period type mismatch for {iid}")
        if record.get("evidence_status") != cfg.get("required_evidence_status"):
            raise ValueError(f"Evidence status mismatch for {iid}")
        if record.get("source_id") not in set(cfg.get("allowed_sources", [])):
            raise ValueError(f"Unapproved source for {iid}: {record.get('source_id')}")
        if record.get("observation_status") != "final":
            raise ValueError(f"Non-final daily record blocked: {record.get('id')}")

        required_sources = int(cfg.get("required_min_independent_sources", 0) or 0)
        source_ids = set(record.get("corroboration_source_ids", []) or [])
        obs_ids = set(record.get("corroboration_observation_ids", []) or [])
        if len(source_ids) < required_sources or len(obs_ids) < required_sources:
            raise ValueError(f"Insufficient corroboration for {iid}")
        if not source_ids.issubset(set(cfg.get("allowed_sources", []))):
            raise ValueError(f"Corroboration includes unapproved source for {iid}: {sorted(source_ids)}")

        period_day = parse_day(record.get("period"))
        age = (today - period_day).days
        if age < 0:
            raise ValueError(f"Future-dated daily record blocked: {iid} {period_day}")
        if age > max_age_days:
            raise ValueError(f"Stale daily record blocked: {iid} {period_day} is {age} days old")
        previous = latest_by_indicator.get(iid)
        if previous and period_day <= previous:
            raise ValueError(f"Non-forward daily period blocked for {iid}: {period_day} <= {previous}")

    current_meta = read_json(repo_meta_path) if repo_meta_path.exists() else {}
    prior_run_number = current_meta.get("source_run_number")
    if additions and auto_policy.get("require_monotonic_source_run_number", True) and prior_run_number is not None:
        if int(source_run_number) <= int(prior_run_number):
            raise ValueError(
                f"Source run number must advance beyond repository run #{prior_run_number}; got #{source_run_number}"
            )

    published_at = now_iso()
    output = deepcopy(incoming)
    output["repository_publish"] = True
    output["frontend_publish"] = False
    output["repository_published_at"] = published_at
    output["repository_source_run_number"] = source_run_number
    output["repository_source_run_database_id"] = str(source_run_database_id)
    output["repository_persistence_mode"] = auto_policy["mode"]

    repo_meta = {
        "schema_version": 1,
        "generated_at": published_at,
        "mode": auto_policy["mode"],
        "repository_publish": True,
        "frontend_publish": False,
        "source_workflow": auto_policy.get("source_workflow"),
        "source_run_number": source_run_number,
        "source_run_database_id": str(source_run_database_id),
        "source_artifact": f"{auto_policy.get('source_artifact_prefix', 'macro-production-')}{source_run_number}",
        "source_promotion_run_id": incoming.get("source_run_id"),
        "source_generated_at": incoming.get("generated_at"),
        "prior_record_count": len(current_records),
        "added_record_count": len(additions),
        "final_record_count": len(incoming_records),
        "observations_sha256": None,
        "rollback": "Use git history/revert. Automatic daily publishing is append-only and retains last good data on failure."
    }

    atomic_write_json(repo_obs_path, output)
    repo_meta["observations_sha256"] = sha256(repo_obs_path)
    atomic_write_json(repo_meta_path, repo_meta)

    report = {
        "schema_version": 1,
        "generated_at": published_at,
        "mode": auto_policy["mode"],
        "status": "ready-to-commit",
        "repository_write": True,
        "git_commit_expected": True,
        "source_run_number": source_run_number,
        "source_run_database_id": str(source_run_database_id),
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
                "corroboration_source_ids": r.get("corroboration_source_ids", []),
            }
            for r in additions
        ],
        "notes": [
            "Only corroborated append-only daily FX/gold additions passed the automatic repository gate.",
            "All other Macro indicators remain under the existing controlled/manual persistence process."
        ],
    }
    write_json(report_dir / "daily-auto-persistence.json", report)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--incoming-dir", required=True)
    ap.add_argument("--repo-processed-dir", default="data/processed/macro")
    ap.add_argument("--report-dir", default="data/staging/daily-auto-persistence")
    ap.add_argument("--source-run-number", required=True, type=int)
    ap.add_argument("--source-run-database-id", required=True)
    ap.add_argument("--policy", default="config/daily_auto_persistence_policy.json")
    ap.add_argument("--daily-gate", default="config/daily_fx_gold_production_gate.json")
    args = ap.parse_args()

    def resolve(value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else ROOT / p

    incoming_dir = resolve(args.incoming_dir)
    repo_dir = resolve(args.repo_processed_dir)
    report_dir = resolve(args.report_dir)
    policy = resolve(args.policy)
    daily_gate = resolve(args.daily_gate)

    allowed_repo = (ROOT / "data/processed/macro").resolve()
    allowed_report = (ROOT / "data/staging/daily-auto-persistence").resolve()
    if repo_dir.resolve() != allowed_repo:
        raise SystemExit(f"Safety violation: repository target must be exactly {allowed_repo}")
    if report_dir.resolve() != allowed_report:
        raise SystemExit(f"Safety violation: report target must be exactly {allowed_report}")

    report = build_daily_persistence(
        incoming_dir,
        repo_dir,
        report_dir,
        args.source_run_number,
        args.source_run_database_id,
        policy,
        daily_gate,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
