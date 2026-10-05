from pathlib import Path
import copy
import json
import shutil
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from promote_production import build_production  # noqa: E402
from promotion_preview import build_preview  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/macro-candidate-6"
PREVIEW_POLICY = ROOT / "config/promotion_policy.json"
FRONTEND_MAPPING = ROOT / "config/frontend_indicator_map.json"
NORMALIZATION = ROOT / "config/indicator_normalization.json"
POLICY = ROOT / "config/production_promotion_policy.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_preview(dst: Path):
    """Build this test's preview from the candidate fixture.

    Do not depend on data/staging/macro-preview already existing in the repository:
    GitHub runners start from a clean checkout and the live preview step runs only
    after fixture tests. build_preview enforces a repository-local staging path, so
    create a temporary staging directory under data/staging and then copy only the
    files this production test needs into its private temp directory.
    """
    staging_root = ROOT / "data/staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    generated = Path(tempfile.mkdtemp(prefix="test-production-preview-", dir=str(staging_root)))
    try:
        build_preview(FIXTURE, generated, PREVIEW_POLICY, FRONTEND_MAPPING, NORMALIZATION)
        dst.mkdir(parents=True, exist_ok=True)
        for name in ["canonical-observations.preview.json", "promotion-manifest.json", "preview-meta.json"]:
            shutil.copy2(generated / name, dst / name)
    finally:
        shutil.rmtree(generated, ignore_errors=True)


def main():
    temp = Path(tempfile.mkdtemp(prefix="production-promotion-test-"))
    try:
        preview = temp / "preview"
        processed = temp / "data/processed/macro"
        make_preview(preview)

        out1, report1 = build_production(preview, processed, POLICY)
        assert out1["record_count"] == 3, out1
        assert report1["added_record_count"] == 3, report1
        assert report1["unchanged_record_count"] == 0, report1
        assert out1["repository_publish"] is False
        assert out1["frontend_publish"] is False
        assert all(r["source_id"] == "nso-vietnam" for r in out1["data"])
        assert all(r["evidence_status"] == "verified" for r in out1["data"])
        assert all("preview_only" not in r for r in out1["data"])

        # Idempotency: different fetch timestamps must not create duplicate facts.
        cp = load(preview / "canonical-observations.preview.json")
        for r in cp["data"]:
            r["fetched_at"] = "2099-01-01T00:00:00+00:00"
        dump(preview / "canonical-observations.preview.json", cp)
        out2, report2 = build_production(preview, processed, POLICY)
        assert out2["record_count"] == 3, out2
        assert report2["added_record_count"] == 0, report2
        assert report2["unchanged_record_count"] == 3, report2

        # Conflict safety: changed value for an existing indicator-period must abort before overwrite.
        before = load(processed / "observations.json")
        changed = copy.deepcopy(cp)
        changed["data"][0]["value"] = changed["data"][0]["value"] + 0.01
        dump(preview / "canonical-observations.preview.json", changed)
        try:
            build_production(preview, processed, POLICY)
            raise AssertionError("Expected historical conflict to block promotion")
        except ValueError as exc:
            assert "historical conflict" in str(exc)
        after = load(processed / "observations.json")
        assert before == after, "Conflict must not mutate canonical observations.json"

        # Per-indicator readiness safety: FX is allowlisted only when ready-corroborated.
        dump(preview / "canonical-observations.preview.json", cp)
        extra = load(preview / "canonical-observations.preview.json")
        extra_record = copy.deepcopy(extra["data"][0])
        extra_record.update({
            "id": "fx-test-id",
            "source_record_id": "fx-test-id",
            "indicator_id": "usd-vnd-central-rate",
            "period": "2026-10-04",
            "period_type": "day",
            "data_date": "2026-10-04",
            "value": 25636,
            "unit": "vnd-per-usd",
            "source_id": "vna-vietnamplus",
            "evidence_status": "corroborated",
            "corroboration_source_ids": ["vna-vietnamplus", "banking-times-vn"],
            "corroboration_observation_ids": ["fx-test-id", "fx-peer-id"],
            "corroboration_reason": "fixture agreement"
        })
        extra["data"].append(extra_record)
        dump(preview / "canonical-observations.preview.json", extra)
        mani = load(preview / "promotion-manifest.json")
        mani["data"].append({
            "indicator_id": "usd-vnd-central-rate",
            "readiness_status": "ready-canonical",
            "action": "promote-canonical-preview",
            "selected_observation_id": "fx-test-id"
        })
        dump(preview / "promotion-manifest.json", mani)
        out3, report3 = build_production(preview, processed, POLICY)
        assert out3["record_count"] == 3
        assert any(x["indicator_id"] == "usd-vnd-central-rate" and x["action"] == "hold-indicator-readiness" for x in report3["held"])

        print("Controlled production promotion tests passed")
    finally:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    main()
