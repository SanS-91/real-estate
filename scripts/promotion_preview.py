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


def index_by_id(records):
    out = {}
    for r in records:
        rid = r.get("id")
        if not rid:
            raise ValueError("Candidate observation missing id")
        if rid in out:
            raise ValueError(f"Duplicate candidate observation id: {rid}")
        out[rid] = r
    return out


def canonical_indicator_id(source_indicator_id: str, normalization_cfg: dict) -> str:
    entry = normalization_cfg.get("mappings", {}).get(source_indicator_id)
    if not entry:
        return source_indicator_id
    if isinstance(entry, str):
        return entry
    return entry.get("canonical_indicator_id") or source_indicator_id


def normalize_record(candidate: dict, source_indicator_id: str, canonical_id: str) -> dict:
    out = dict(candidate)
    out["indicator_id"] = canonical_id
    if source_indicator_id != canonical_id:
        out["source_indicator_id"] = source_indicator_id
    return out


def canonicalize(candidate: dict, preview_generated_at: str, policy: dict, readiness_item: dict,
                 source_indicator_id: str, canonical_id: str) -> dict:
    out = normalize_record(candidate, source_indicator_id, canonical_id)
    source_record_id = candidate["id"]
    if policy.get("preserve_candidate_ids_as_source_record_id", True):
        out["source_record_id"] = source_record_id

    readiness_status = readiness_item.get("status")
    if readiness_status == "ready-corroborated":
        independent_sources = list(dict.fromkeys(readiness_item.get("independent_sources", []) or []))
        evidence_ids = list(dict.fromkeys(readiness_item.get("evidence_observation_ids", []) or []))
        if len(independent_sources) < 2 or len(evidence_ids) < 2:
            raise ValueError(f"{source_indicator_id}: ready-corroborated requires at least two independent sources/evidence records")
        # The selected source observation may itself be marked 'reported'. The promoted
        # preview represents the pool-level evidence conclusion, so its evidence status
        # is upgraded to 'corroborated' while preserving all source-level provenance.
        out["evidence_status"] = "corroborated"
        out["corroboration_source_ids"] = independent_sources
        out["corroboration_observation_ids"] = evidence_ids
        out["corroboration_reason"] = readiness_item.get("reason")

    out["observation_status"] = policy.get("canonical_observation_status", "final")
    out["preview_promoted_at"] = preview_generated_at
    out["preview_only"] = True
    return out


def evidence_copy(candidate: dict, preview_generated_at: str, source_indicator_id: str, canonical_id: str) -> dict:
    out = normalize_record(candidate, source_indicator_id, canonical_id)
    out["source_record_id"] = candidate["id"]
    out["preview_reviewed_at"] = preview_generated_at
    out["preview_only"] = True
    return out


def build_preview(candidate_dir: Path, output_dir: Path, policy_path: Path, mapping_path: Path, normalization_path: Path):
    policy = read_json(policy_path)
    if policy.get("mode") != "dry-run-only" or policy.get("production_write") is not False:
        raise ValueError("Safety violation: promotion preview must remain dry-run-only with production_write=false")

    observations_payload = read_json(candidate_dir / "observations.json")
    readiness_payload = read_json(candidate_dir / "publish-readiness.json")
    run_report = read_json(candidate_dir / "run-report.json")
    mapping_cfg = read_json(mapping_path)
    normalization_cfg = read_json(normalization_path)

    observations = observations_payload.get("data", [])
    by_id = index_by_id(observations)
    readiness = readiness_payload.get("data", [])
    preview_generated_at = now_iso()

    canonical_statuses = set(policy.get("canonical_readiness_statuses", []))
    evidence_statuses = set(policy.get("evidence_readiness_statuses", []))
    missing_statuses = set(policy.get("missing_readiness_statuses", []))

    canonical = []
    evidence = []
    manifest_rows = []
    seen_selected = set()

    for item in readiness:
        source_iid = item.get("indicator_id")
        iid = canonical_indicator_id(source_iid, normalization_cfg)
        status = item.get("status")
        selected_id = item.get("selected_observation_id")
        evidence_ids = item.get("evidence_observation_ids", []) or []

        if status in canonical_statuses:
            if not selected_id:
                raise ValueError(f"{source_iid}: {status} without selected_observation_id")
            if selected_id not in by_id:
                raise ValueError(f"{source_iid}: selected observation {selected_id} not found in candidate observations")
            if selected_id in seen_selected:
                raise ValueError(f"Observation selected more than once: {selected_id}")
            seen_selected.add(selected_id)
            row = canonicalize(by_id[selected_id], preview_generated_at, policy, item, source_iid, iid)
            canonical.append(row)
            action = "promote-canonical-preview"
            selected = row
        elif status in evidence_statuses:
            for eid in evidence_ids:
                if eid not in by_id:
                    raise ValueError(f"{source_iid}: evidence observation {eid} not found")
                evidence.append(evidence_copy(by_id[eid], preview_generated_at, source_iid, iid))
            action = "hold-evidence"
            selected = normalize_record(by_id[evidence_ids[0]], source_iid, iid) if evidence_ids else None
        elif status in missing_statuses:
            action = "hold-missing"
            selected = None
        else:
            action = "hold-unknown-status"
            selected = None

        mapping = mapping_cfg.get("mappings", {}).get(iid, {"frontend_indicator_id": None, "status": "unmapped"})
        manifest_rows.append({
            "indicator_id": iid,
            "source_indicator_id": source_iid if source_iid != iid else None,
            "readiness_status": status,
            "action": action,
            "selected_observation_id": selected_id,
            "evidence_observation_ids": evidence_ids,
            "independent_sources": item.get("independent_sources", []) or [],
            "reason": item.get("reason"),
            "value": selected.get("value") if selected else None,
            "unit": selected.get("unit") if selected else None,
            "period": selected.get("period") if selected else None,
            "source_id": selected.get("source_id") if selected else None,
            "evidence_status": selected.get("evidence_status") if selected else None,
            "frontend_indicator_id": mapping.get("frontend_indicator_id"),
            "frontend_compatibility": mapping.get("status", "unmapped")
        })

    canonical_ids = {x["id"] for x in canonical}
    evidence = [x for x in evidence if x["id"] not in canonical_ids]

    canonical.sort(key=lambda r: (r.get("indicator_id", ""), r.get("period") or "", r.get("id", "")))
    evidence.sort(key=lambda r: (r.get("indicator_id", ""), r.get("period") or "", r.get("id", "")))
    manifest_rows.sort(key=lambda r: r.get("indicator_id", ""))

    meta = {
        "schema_version": 2,
        "mode": "dry-run-promotion-preview",
        "production_write": False,
        "source_run_id": run_report.get("run_id"),
        "candidate_generated_at": observations_payload.get("generated_at"),
        "preview_generated_at": preview_generated_at,
        "candidate_record_count": len(observations),
        "canonical_preview_count": len(canonical),
        "evidence_preview_count": len(evidence),
        "frontend_baseline": mapping_cfg.get("frontend_baseline"),
        "indicator_normalization_schema_version": normalization_cfg.get("schema_version"),
        "notes": [
            "candidate_generated_at is inherited from the collector run metadata and is not treated as completion time.",
            "preview_generated_at is the completion time for this dry-run preview.",
            "Source-layer indicator IDs may be normalized before production; source_indicator_id preserves the original collector ID.",
            "ready-corroborated observations carry pool-level evidence_status=corroborated plus independent source provenance.",
            "No data/processed production path is read or written by this tool."
        ]
    }

    canonical_payload = {
        "schema_version": 2,
        "generated_at": preview_generated_at,
        "record_count": len(canonical),
        "preview_only": True,
        "source_run_id": run_report.get("run_id"),
        "data": canonical,
    }
    evidence_payload = {
        "schema_version": 2,
        "generated_at": preview_generated_at,
        "record_count": len(evidence),
        "preview_only": True,
        "source_run_id": run_report.get("run_id"),
        "data": evidence,
    }
    manifest = {
        "schema_version": 2,
        "generated_at": preview_generated_at,
        "production_write": False,
        "source_run_id": run_report.get("run_id"),
        "data": manifest_rows,
    }

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp_parent = output_dir.parent / ".preview-tmp"
    tmp_parent.mkdir(parents=True, exist_ok=True)
    build_dir = Path(tempfile.mkdtemp(prefix="macro-promotion-preview-", dir=str(tmp_parent)))
    try:
        write_json(build_dir / "canonical-observations.preview.json", canonical_payload)
        write_json(build_dir / "evidence-observations.preview.json", evidence_payload)
        write_json(build_dir / "promotion-manifest.json", manifest)
        write_json(build_dir / "preview-meta.json", meta)
        with (build_dir / "promotion-summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
            fields = [
                "indicator_id", "source_indicator_id", "readiness_status", "action", "value", "unit", "period", "source_id",
                "evidence_status", "frontend_indicator_id", "frontend_compatibility", "reason"
            ]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in manifest_rows:
                w.writerow({k: row.get(k) for k in fields})

        if output_dir.exists():
            shutil.rmtree(output_dir)
        os.replace(build_dir, output_dir)
    finally:
        if build_dir.exists():
            shutil.rmtree(build_dir, ignore_errors=True)
        try:
            tmp_parent.rmdir()
        except OSError:
            pass

    return meta, manifest_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-dir", default="data/candidate/macro")
    ap.add_argument("--output-dir", default="data/staging/macro-preview")
    ap.add_argument("--policy", default="config/promotion_policy.json")
    ap.add_argument("--frontend-map", default="config/frontend_indicator_map.json")
    ap.add_argument("--indicator-normalization", default="config/indicator_normalization.json")
    args = ap.parse_args()

    def resolve_arg(value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else ROOT / p

    candidate_dir = resolve_arg(args.candidate_dir)
    output_dir = resolve_arg(args.output_dir)
    policy_path = resolve_arg(args.policy)
    mapping_path = resolve_arg(args.frontend_map)
    normalization_path = resolve_arg(args.indicator_normalization)

    resolved_out = output_dir.resolve()
    allowed_root = (ROOT / "data/staging").resolve()
    processed_root = (ROOT / "data/processed").resolve()
    if processed_root == resolved_out or processed_root in resolved_out.parents:
        raise SystemExit("Safety violation: dry-run promotion engine cannot write to data/processed")
    if allowed_root != resolved_out and allowed_root not in resolved_out.parents:
        raise SystemExit(f"Safety violation: output must remain under {allowed_root}")

    meta, manifest = build_preview(candidate_dir, output_dir, policy_path, mapping_path, normalization_path)
    print(json.dumps({"meta": meta, "manifest": manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
