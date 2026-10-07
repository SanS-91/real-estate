from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
from jsonschema import Draft202012Validator, FormatChecker

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--processed-dir", default="data/processed/macro")
    ap.add_argument("--schema", default="schemas/processed_macro_observation.schema.json")
    ap.add_argument("--production-policy", default="config/production_promotion_policy.json")
    ap.add_argument("--persistence-policy", default="config/repository_persistence_policy.json")
    ap.add_argument("--auto-persistence-policy", default="config/daily_auto_persistence_policy.json")
    args = ap.parse_args()

    def resolve(value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else ROOT / p

    processed_dir = resolve(args.processed_dir)
    payload = read_json(processed_dir / "observations.json")
    meta = read_json(processed_dir / "repository-publish.json")
    schema = read_json(resolve(args.schema))
    production_policy = read_json(resolve(args.production_policy))
    persistence_policy = read_json(resolve(args.persistence_policy))
    auto_persistence_policy = read_json(resolve(args.auto_persistence_policy))

    errors = []
    records = payload.get("data", [])
    if payload.get("record_count") != len(records):
        errors.append("observations.json record_count does not match data length")
    if payload.get("production_write") is not True:
        errors.append("observations.json production_write must be true")
    if payload.get("repository_publish") is not True:
        errors.append("repository observations must set repository_publish=true")
    if payload.get("frontend_publish") is not False:
        errors.append("Repository persistence must keep frontend_publish=false")
    allowed_persistence_modes = {persistence_policy.get("mode"), auto_persistence_policy.get("mode")}
    payload_mode = payload.get("repository_persistence_mode")
    meta_mode = meta.get("mode")
    if payload_mode not in allowed_persistence_modes:
        errors.append("repository_persistence_mode mismatch")
    if meta_mode != payload_mode:
        errors.append("repository persistence mode mismatch between observations and metadata")
    if meta.get("repository_publish") is not True or meta.get("frontend_publish") is not False:
        errors.append("repository-publish.json flags are invalid")
    if meta.get("final_record_count") != len(records):
        errors.append("repository-publish.json final_record_count mismatch")
    if str(meta.get("source_run_number")) != str(payload.get("repository_source_run_number")):
        errors.append("source run number mismatch between observations and repository metadata")
    h = hashlib.sha256((processed_dir / "observations.json").read_bytes()).hexdigest()
    if meta.get("observations_sha256") != h:
        errors.append("repository-publish.json observations_sha256 mismatch")

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    allowed = production_policy.get("allowed_indicators", {})
    key_fields = production_policy.get("logical_key_fields", ["indicator_id", "period_type", "period"])
    ids = set()
    keys = set()
    for idx, r in enumerate(records):
        for e in validator.iter_errors(r):
            errors.append(f"record {idx}: {e.message}")
        rid = r.get("id")
        if not rid or rid in ids:
            errors.append(f"record {idx}: missing/duplicate id {rid}")
        ids.add(rid)
        key = tuple(r.get(k) for k in key_fields)
        if key in keys:
            errors.append(f"record {idx}: duplicate logical key {key}")
        keys.add(key)
        cfg = allowed.get(r.get("indicator_id"))
        if not cfg:
            errors.append(f"record {idx}: indicator not allowlisted: {r.get('indicator_id')}")
        else:
            if r.get("source_id") not in cfg.get("allowed_sources", []):
                errors.append(f"record {idx}: source not allowlisted: {r.get('source_id')}")
            if r.get("evidence_status") != cfg.get("required_evidence_status"):
                errors.append(f"record {idx}: evidence status mismatch")
            if r.get("period_type") != cfg.get("required_period_type"):
                errors.append(f"record {idx}: period type mismatch")
            min_sources = int(cfg.get("required_min_independent_sources", 0) or 0)
            if min_sources:
                source_ids = list(dict.fromkeys(r.get("corroboration_source_ids", []) or []))
                observation_ids = list(dict.fromkeys(r.get("corroboration_observation_ids", []) or []))
                if len(source_ids) < min_sources or len(observation_ids) < min_sources:
                    errors.append(f"record {idx}: insufficient corroboration provenance")
        if r.get("observation_status") != "final":
            errors.append(f"record {idx}: observation_status must be final")
        if any(k.startswith("preview_") for k in r) or "preview_only" in r:
            errors.append(f"record {idx}: preview-only field leaked into repository production")

    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(json.dumps({
        "valid": True,
        "record_count": len(records),
        "repository_publish": True,
        "frontend_publish": False,
        "source_run_number": meta.get("source_run_number"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
