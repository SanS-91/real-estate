from __future__ import annotations

from pathlib import Path
import argparse
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
    ap.add_argument("--policy", default="config/production_promotion_policy.json")
    args = ap.parse_args()

    def resolve(value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else ROOT / p

    processed_dir = resolve(args.processed_dir)
    schema = read_json(resolve(args.schema))
    policy = read_json(resolve(args.policy))
    payload = read_json(processed_dir / "observations.json")
    report = read_json(processed_dir / "promotion-run.json")

    errors = []
    records = payload.get("data", [])
    if payload.get("record_count") != len(records):
        errors.append("observations.json record_count does not match data length")
    if payload.get("production_write") is not True:
        errors.append("observations.json production_write must be true")
    if payload.get("repository_publish") is not False or payload.get("frontend_publish") is not False:
        errors.append("Controlled production must keep repository_publish=false and frontend_publish=false")
    if report.get("conflict_count") != 0:
        errors.append("promotion-run conflict_count must be zero")
    if report.get("final_record_count") != len(records):
        errors.append("promotion-run final_record_count mismatch")

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    allowed = policy.get("allowed_indicators", {})
    key_fields = policy.get("logical_key_fields", ["indicator_id", "period_type", "period"])
    ids = set()
    keys = set()
    for idx, r in enumerate(records):
        for e in validator.iter_errors(r):
            errors.append(f"record {idx}: {e.message}")
        rid = r.get("id")
        if rid in ids:
            errors.append(f"record {idx}: duplicate id {rid}")
        ids.add(rid)
        key = tuple(r.get(k) for k in key_fields)
        if key in keys:
            errors.append(f"record {idx}: duplicate logical key {key}")
        keys.add(key)
        cfg = allowed.get(r.get("indicator_id"))
        if not cfg:
            errors.append(f"record {idx}: indicator not allowlisted for Phase 4.2E: {r.get('indicator_id')}")
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
        if any(k.startswith("preview_") for k in r.keys()) or "preview_only" in r:
            errors.append(f"record {idx}: preview-only field leaked into production")

    prior_count = report.get("prior_record_count", 0)
    final_count = report.get("final_record_count", 0)
    if final_count < prior_count:
        errors.append("record-drop anomaly: final count is lower than prior count")

    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(json.dumps({
        "valid": True,
        "record_count": len(records),
        "added_record_count": report.get("added_record_count"),
        "unchanged_record_count": report.get("unchanged_record_count"),
        "repository_publish": payload.get("repository_publish"),
        "frontend_publish": payload.get("frontend_publish")
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
