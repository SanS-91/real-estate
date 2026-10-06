from pathlib import Path
import copy
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from promotion_preview import build_preview
from promote_production import build_production
from persist_repository import build_repository_persistence

MAIN_POLICY = ROOT / "config/production_promotion_policy.json"
GATE_POLICY = ROOT / "config/policy_rates_production_gate.json"
PREVIEW_POLICY = ROOT / "config/promotion_policy.json"
FRONTEND = ROOT / "config/frontend_indicator_map.json"
NORMALIZATION = ROOT / "config/indicator_normalization.json"
PERSIST_POLICY = ROOT / "config/repository_persistence_policy.json"
BASE_PROCESSED = ROOT / "data/processed/macro"

POLICY_VALUES = {
    "policy-refinancing-rate": 4.5,
    "policy-rediscount-rate": 3.0,
    "policy-overnight-lending-rate": 5.0,
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_policy_candidate(out: Path):
    cmd = [
        sys.executable,
        str(ROOT / "scripts/candidate_pipeline.py"),
        "--fixture-mode",
        "--replace-history",
        "--output-root",
        str(out),
        "--source",
        "vietnamplus-policy-rates",
        "--source",
        "banking-times-policy-rates",
    ]
    cp = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if cp.returncode != 0:
        raise AssertionError(cp.stdout + "\n" + cp.stderr)


def main():
    main_policy = load(MAIN_POLICY)
    gate_policy = load(GATE_POLICY)

    # Main production policy must allow exactly the trusted two-source policy facts.
    for iid in POLICY_VALUES:
        cfg = main_policy["allowed_indicators"][iid]
        assert set(cfg["allowed_sources"]) == {"vna-vietnamplus", "banking-times-vn"}
        assert cfg["required_readiness_statuses"] == ["ready-corroborated"]
        assert cfg["required_evidence_status"] == "corroborated"
        assert cfg["required_period_type"] == "date"
        assert cfg["required_min_independent_sources"] == 2
    assert "interbank-on" not in main_policy["allowed_indicators"]

    # Narrow gate is deliberately policy-only so cached daily FX/gold cannot sneak into K3.
    assert set(gate_policy["allowed_indicators"]) == set(POLICY_VALUES)

    workflow = (ROOT / ".github/workflows/macro-candidate.yml").read_text(encoding="utf-8")
    assert "policy-rates-production" in workflow
    assert "--policy config/policy_rates_production_gate.json" in workflow
    assert "github.event.inputs.source == 'policy-rates-production'" in workflow

    temp = Path(tempfile.mkdtemp(prefix="phase4-2k3-"))
    staging_root = ROOT / "data/staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    preview_dir = Path(tempfile.mkdtemp(prefix="k3-preview-", dir=staging_root))
    try:
        candidate = temp / "candidate"
        build_policy_candidate(candidate)
        readiness = load(candidate / "publish-readiness.json")
        by = {x["indicator_id"]: x for x in readiness["data"]}
        for iid in POLICY_VALUES:
            assert by[iid]["status"] == "ready-corroborated"
            assert by[iid]["latest_business_period"] == "2023-06-19"
            assert set(by[iid]["independent_sources"]) == {"vna-vietnamplus", "banking-times-vn"}

        build_preview(candidate, preview_dir, PREVIEW_POLICY, FRONTEND, NORMALIZATION)
        canonical_path = preview_dir / "canonical-observations.preview.json"
        manifest_path = preview_dir / "promotion-manifest.json"
        canonical = load(canonical_path)
        manifest = load(manifest_path)
        selected = {r["indicator_id"]: r for r in canonical["data"]}
        assert set(selected) == set(POLICY_VALUES)
        for iid, value in POLICY_VALUES.items():
            r = selected[iid]
            assert r["value"] == value
            assert r["period"] == "2023-06-19"
            assert r["period_type"] == "date"
            assert r["evidence_status"] == "corroborated"
            assert set(r["corroboration_source_ids"]) == {"vna-vietnamplus", "banking-times-vn"}

        # Inject a newer ready-corroborated FX preview to prove the targeted K3 gate holds it.
        fx = copy.deepcopy(next(iter(selected.values())))
        fx.update({
            "id": "k3-fx-2026-10-06",
            "source_record_id": "k3-fx-2026-10-06",
            "indicator_id": "usd-vnd-central-rate",
            "period": "2026-10-06",
            "period_type": "day",
            "data_date": "2026-10-06",
            "value": 25645.0,
            "unit": "vnd-per-usd",
            "source_id": "vna-vietnamplus",
            "source_url": "https://example.test/fx",
            "published_at": "2026-10-06",
            "evidence_status": "corroborated",
            "corroboration_source_ids": ["vna-vietnamplus", "banking-times-vn"],
            "corroboration_observation_ids": ["k3-fx-2026-10-06", "k3-fx-peer"],
        })
        canonical["data"].append(fx)
        canonical["record_count"] = len(canonical["data"])
        dump(canonical_path, canonical)
        manifest["data"].append({
            "indicator_id": "usd-vnd-central-rate",
            "readiness_status": "ready-corroborated",
            "action": "promote-canonical-preview",
            "selected_observation_id": fx["id"],
        })
        dump(manifest_path, manifest)

        processed = temp / "processed"
        processed.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE_PROCESSED / "observations.json", processed / "observations.json")
        out, report = build_production(preview_dir, processed, GATE_POLICY)
        # Repository baseline is post-K3 persistence: the three policy records already exist.
        # Re-running the narrow gate must be idempotent and must still hold unrelated FX.
        assert report["prior_record_count"] == 15, report
        assert report["added_record_count"] == 0, report
        assert report["unchanged_record_count"] == 3, report
        assert report["final_record_count"] == 15, report
        assert {r["indicator_id"] for r in report["unchanged"]} == set(POLICY_VALUES)
        assert any(h["indicator_id"] == "usd-vnd-central-rate" and h["action"] == "hold-not-allowlisted" for h in report["held"])
        assert all(r["indicator_id"] != "interbank-on" for r in out["data"])

        # Validate the full 15-record artifact against the normal production policy.
        cp = subprocess.run([
            sys.executable,
            str(ROOT / "scripts/validate_production.py"),
            "--processed-dir",
            str(processed),
            "--policy",
            str(MAIN_POLICY),
        ], cwd=ROOT, capture_output=True, text=True)
        if cp.returncode != 0:
            raise AssertionError(cp.stdout + "\n" + cp.stderr)

        # Persistence simulation is idempotent against the current 15-record repository state.
        repo_copy = temp / "repo-processed"
        repo_copy.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE_PROCESSED / "observations.json", repo_copy / "observations.json")
        shutil.copy2(BASE_PROCESSED / "repository-publish.json", repo_copy / "repository-publish.json")
        persist_report = build_repository_persistence(
            processed,
            repo_copy,
            temp / "persistence-report",
            999,
            "fixture-k3",
            PERSIST_POLICY,
            MAIN_POLICY,
        )
        assert persist_report["status"] == "no-change", persist_report
        assert persist_report["prior_record_count"] == 15
        assert persist_report["added_record_count"] == 0
        assert persist_report["final_record_count"] == 15

        print("Phase 4.2K.3 policy production gate tests PASS")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
        shutil.rmtree(preview_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
