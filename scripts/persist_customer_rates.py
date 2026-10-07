from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse, hashlib, json, os, tempfile

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def atomic_write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="customer-rates-persist-", dir=str(path.parent)))
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def logical_key(record: dict, fields: list[str]) -> tuple:
    values = tuple(record.get(k) for k in fields)
    if any(v in (None, "") for v in values):
        raise ValueError(f"Missing logical-key field for record {record.get('id')}: {fields}")
    return values


def make_index(records: list[dict], key_fields: list[str]) -> dict[tuple, dict]:
    out = {}
    ids = set()
    for record in records:
        rid = record.get("id")
        if not rid or rid in ids:
            raise ValueError(f"Missing/duplicate record id: {rid}")
        ids.add(rid)
        key = logical_key(record, key_fields)
        if key in out:
            raise ValueError(f"Duplicate logical key: {key}")
        out[key] = record
    return out


def parse_month(value: str) -> tuple[int, int]:
    try:
        dt = datetime.strptime(value, "%Y-%m")
        return dt.year, dt.month
    except Exception as exc:
        raise ValueError(f"Customer-rate auto-publish requires YYYY-MM period; got {value!r}") from exc


def month_index(value: tuple[int, int]) -> int:
    return value[0] * 12 + value[1] - 1


def build_customer_rates_persistence(
    incoming_dir: Path,
    repo_processed_dir: Path,
    report_dir: Path,
    source_run_number: int,
    source_run_database_id: str,
    auto_policy_path: Path,
    gate_path: Path,
    as_of: datetime | None = None,
):
    policy = read_json(auto_policy_path)
    gate = read_json(gate_path)
    if policy.get("mode") != "controlled-customer-rates-auto-persistence-v1":
        raise ValueError("Safety violation: invalid customer-rate auto-persistence policy")
    if policy.get("repository_publish") is not True or policy.get("frontend_publish") is not False:
        raise ValueError("Safety violation: customer-rate policy must publish repository only")
    if gate.get("mode") != "controlled-production-v1" or gate.get("production_write") is not True:
        raise ValueError("Safety violation: invalid customer-rate production gate")

    incoming = read_json(incoming_dir / "observations.json")
    run = read_json(incoming_dir / "promotion-run.json")
    incoming_records = incoming.get("data", [])
    if incoming.get("record_count") != len(incoming_records):
        raise ValueError("Incoming record_count mismatch")
    if incoming.get("production_write") is not True or incoming.get("repository_publish") is not False:
        raise ValueError("Incoming file is not pre-persistence controlled production")
    if incoming.get("frontend_publish") is not False:
        raise ValueError("Incoming production unexpectedly enables frontend publishing")
    if run.get("mode") != "controlled-production-v1" or run.get("conflict_count") != 0:
        raise ValueError("Incoming production run is not conflict-free controlled production")
    if run.get("final_record_count") != len(incoming_records):
        raise ValueError("Incoming promotion-run final_record_count mismatch")
    if run.get("source_run_id") != incoming.get("source_run_id"):
        raise ValueError("Incoming promotion run id mismatch")

    repo_obs = repo_processed_dir / "observations.json"
    repo_meta = repo_processed_dir / "repository-publish.json"
    current = read_json(repo_obs)
    current_records = current.get("data", [])
    if current.get("record_count") != len(current_records):
        raise ValueError("Repository record_count mismatch")
    if current.get("repository_publish") is not True:
        raise ValueError("Current repository observations are not canonical repository data")

    key_fields = list(policy.get("logical_key_fields", ["indicator_id", "period_type", "period"]))
    old_index = make_index(current_records, key_fields)
    new_index = make_index(incoming_records, key_fields)
    if policy.get("require_prior_count_match", True) and run.get("prior_record_count") != len(current_records):
        raise ValueError(
            f"Stale baseline blocked: production prior_record_count={run.get('prior_record_count')}, repository count={len(current_records)}"
        )
    for key, old in old_index.items():
        new = new_index.get(key)
        if new is None:
            raise ValueError(f"Record-drop blocked: {key}")
        if new != old:
            raise ValueError(f"Historical mutation blocked: {key}")

    additions = [record for key, record in new_index.items() if key not in old_index]
    if not additions:
        report = {
            "schema_version": 1, "generated_at": now_iso(), "mode": policy["mode"], "status": "no-change",
            "repository_write": False, "git_commit_expected": False, "source_run_number": source_run_number,
            "source_run_database_id": str(source_run_database_id), "prior_record_count": len(current_records),
            "added_record_count": 0, "final_record_count": len(current_records),
            "notes": ["No new fully corroborated customer-rate bundle; repository remains unchanged."]
        }
        write_json(report_dir / "customer-rates-auto-persistence.json", report)
        return report

    allowed_ids = set(policy.get("allowed_indicator_ids", []))
    required_bundle = int(policy.get("required_bundle_size", len(allowed_ids)))
    if len(additions) != required_bundle or {r.get("indicator_id") for r in additions} != allowed_ids:
        raise ValueError("Safety stop: customer-rate auto-persistence requires one complete four-component bundle")
    if len(additions) > int(policy.get("max_additions_per_run", 4)):
        raise ValueError("Safety stop: customer-rate additions exceed configured maximum")

    periods = {r.get("period") for r in additions}
    if len(periods) != 1:
        raise ValueError(f"Customer-rate bundle must use one common month; got {sorted(periods)}")
    bundle_period = next(iter(periods))

    gate_allowed = gate.get("allowed_indicators", {})
    required_sources = set(policy.get("required_corroboration_source_ids", []))
    local_now = as_of.astimezone(ZoneInfo(policy.get("timezone", "Asia/Ho_Chi_Minh"))) if as_of else datetime.now(ZoneInfo(policy.get("timezone", "Asia/Ho_Chi_Minh")))
    lag = month_index((local_now.year, local_now.month)) - month_index(parse_month(bundle_period))
    if lag < 0:
        raise ValueError(f"Future-dated customer-rate bundle blocked: {bundle_period}")
    if lag > int(policy.get("max_period_lag_months", 3)):
        raise ValueError(f"Stale customer-rate bundle blocked: {bundle_period} is {lag} month(s) behind")

    latest = {}
    for row in current_records:
        iid = row.get("indicator_id")
        if iid in allowed_ids and row.get("period_type") == "month":
            p = row.get("period")
            if iid not in latest or p > latest[iid]:
                latest[iid] = p

    for row in additions:
        iid = row.get("indicator_id")
        cfg = gate_allowed.get(iid)
        if not cfg:
            raise ValueError(f"Indicator not in customer-rate gate: {iid}")
        if row.get("period_type") != "month" or row.get("evidence_status") != "corroborated":
            raise ValueError(f"Customer-rate evidence/period mismatch for {iid}")
        if row.get("source_id") not in set(cfg.get("allowed_sources", [])):
            raise ValueError(f"Unapproved customer-rate source for {iid}: {row.get('source_id')}")
        if row.get("observation_status") != "final":
            raise ValueError(f"Non-final customer-rate record blocked: {row.get('id')}")
        if required_sources - set(row.get("corroboration_source_ids", [])):
            raise ValueError(f"Missing required corroboration sources for {iid}")
        if any(k.startswith("preview_") for k in row) or "preview_only" in row:
            raise ValueError(f"Preview-only field leaked into customer-rate record: {row.get('id')}")
        if latest.get(iid) and bundle_period <= latest[iid]:
            raise ValueError(f"Non-forward customer-rate period blocked for {iid}: {bundle_period} <= {latest[iid]}")

    old_meta = read_json(repo_meta) if repo_meta.exists() else {}
    prior_run = old_meta.get("source_run_number")
    if policy.get("require_monotonic_source_run_number", True) and prior_run is not None and int(source_run_number) <= int(prior_run):
        raise ValueError(f"Source run number must advance beyond repository run #{prior_run}; got #{source_run_number}")

    published_at = now_iso()
    output = deepcopy(incoming)
    output.update({
        "repository_publish": True,
        "frontend_publish": False,
        "repository_published_at": published_at,
        "repository_source_run_number": source_run_number,
        "repository_source_run_database_id": str(source_run_database_id),
        "repository_persistence_mode": policy["mode"],
    })
    meta = {
        "schema_version": 1, "generated_at": published_at, "mode": policy["mode"], "repository_publish": True,
        "frontend_publish": False, "source_workflow": policy.get("source_workflow"), "source_run_number": source_run_number,
        "source_run_database_id": str(source_run_database_id),
        "source_artifact": f"{policy.get('source_artifact_prefix', 'macro-production-')}{source_run_number}",
        "source_promotion_run_id": incoming.get("source_run_id"), "source_generated_at": incoming.get("generated_at"),
        "prior_record_count": len(current_records), "added_record_count": len(additions), "final_record_count": len(incoming_records),
        "observations_sha256": None,
        "rollback": "Use git history/revert. Customer-rate automation is complete-bundle, append-only, and retain-last-good."
    }
    atomic_write_json(repo_obs, output)
    meta["observations_sha256"] = sha256(repo_obs)
    atomic_write_json(repo_meta, meta)

    report = {
        "schema_version": 1, "generated_at": published_at, "mode": policy["mode"], "status": "ready-to-commit",
        "repository_write": True, "git_commit_expected": True, "source_run_number": source_run_number,
        "source_run_database_id": str(source_run_database_id), "prior_record_count": len(current_records),
        "added_record_count": len(additions), "final_record_count": len(incoming_records),
        "observations_sha256": meta["observations_sha256"], "period": bundle_period,
        "added": [{"indicator_id": r.get("indicator_id"), "period": r.get("period"), "value": r.get("value"), "unit": r.get("unit"), "source_id": r.get("source_id"), "corroboration_source_ids": r.get("corroboration_source_ids", [])} for r in additions],
        "notes": ["A complete two-source corroborated customer-rate range bundle passed the automatic repository gate."]
    }
    write_json(report_dir / "customer-rates-auto-persistence.json", report)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--incoming-dir", required=True)
    ap.add_argument("--repo-processed-dir", default="data/processed/macro")
    ap.add_argument("--report-dir", default="data/staging/customer-rates-auto-persistence")
    ap.add_argument("--source-run-number", required=True, type=int)
    ap.add_argument("--source-run-database-id", required=True)
    ap.add_argument("--policy", default="config/customer_rates_auto_persistence_policy.json")
    ap.add_argument("--gate", default="config/customer_rates_production_gate.json")
    args = ap.parse_args()
    resolve = lambda v: Path(v) if Path(v).is_absolute() else ROOT / v
    repo = resolve(args.repo_processed_dir); report = resolve(args.report_dir)
    if repo.resolve() != (ROOT / "data/processed/macro").resolve():
        raise SystemExit("Safety violation: invalid repository target")
    if report.resolve() != (ROOT / "data/staging/customer-rates-auto-persistence").resolve():
        raise SystemExit("Safety violation: invalid report target")
    result = build_customer_rates_persistence(resolve(args.incoming_dir), repo, report, args.source_run_number, args.source_run_database_id, resolve(args.policy), resolve(args.gate))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
