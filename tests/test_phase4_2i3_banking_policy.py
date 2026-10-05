from pathlib import Path
import copy
import json
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from promote_production import build_production

POLICY = ROOT / "config/production_promotion_policy.json"


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_record(iid: str, value: float, rid: str):
    return {
        "id": rid,
        "source_record_id": rid,
        "indicator_id": iid,
        "period": "2026-09",
        "period_type": "month",
        "data_date": "2026-09-28",
        "value": value,
        "unit": "percent",
        "source_id": "nso-vietnam",
        "source_url": "https://www.nso.gov.vn/bai-top/2026/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/",
        "published_at": "2026-10-03",
        "fetched_at": "2026-10-05T07:09:18+00:00",
        "evidence_status": "verified",
        "observation_status": "final",
        "methodology_note": "Official NSO banking activity release",
        "preview_only": True,
    }


def make_preview(path: Path):
    rows = [
        canonical_record("credit-growth-ytd", 10.89, "bank-credit-sep"),
        canonical_record("bank-funding-growth-ytd", 9.78, "bank-funding-sep"),
    ]
    dump(path / "canonical-observations.preview.json", {
        "schema_version": 1,
        "source_run_id": "phase4-2i3-fixture",
        "preview_only": True,
        "record_count": len(rows),
        "data": rows,
    })
    dump(path / "promotion-manifest.json", {
        "schema_version": 1,
        "production_write": False,
        "data": [
            {
                "indicator_id": r["indicator_id"],
                "readiness_status": "ready-canonical",
                "action": "promote-canonical-preview",
                "selected_observation_id": r["id"],
            } for r in rows
        ],
    })
    dump(path / "preview-meta.json", {
        "schema_version": 1,
        "source_run_id": "phase4-2i3-fixture",
    })


def main():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    allowed = policy["allowed_indicators"]
    for iid in ("credit-growth-ytd", "bank-funding-growth-ytd"):
        cfg = allowed[iid]
        assert cfg["allowed_sources"] == ["nso-vietnam"]
        assert cfg["required_readiness_statuses"] == ["ready-canonical"]
        assert cfg["required_evidence_status"] == "verified"
        assert cfg["required_period_type"] == "month"

    temp = Path(tempfile.mkdtemp(prefix="phase4-2i3-policy-"))
    try:
        preview = temp / "preview"
        processed = temp / "processed"
        make_preview(preview)

        output, report = build_production(preview, processed, POLICY)
        assert output["record_count"] == 2, output
        assert report["added_record_count"] == 2, report
        assert report["held_record_count"] == 0, report
        by_id = {r["indicator_id"]: r for r in output["data"]}
        assert by_id["credit-growth-ytd"]["value"] == 10.89
        assert by_id["bank-funding-growth-ytd"]["value"] == 9.78
        assert all(r["source_id"] == "nso-vietnam" for r in output["data"])
        assert all(r["evidence_status"] == "verified" for r in output["data"])

        # Safety: a non-NSO source must be held even if it claims verified/canonical status.
        bad = json.loads((preview / "canonical-observations.preview.json").read_text(encoding="utf-8"))
        bad["data"][0]["source_id"] = "unapproved-bank-source"
        dump(preview / "canonical-observations.preview.json", bad)
        bad_processed = temp / "processed-bad"
        output_bad, report_bad = build_production(preview, bad_processed, POLICY)
        assert output_bad["record_count"] == 1
        assert any(x["indicator_id"] == "credit-growth-ytd" and x["action"] == "hold-source" for x in report_bad["held"])

        # Safety: monthly official indicators cannot enter production with a daily period type.
        make_preview(preview)
        wrong_period = json.loads((preview / "canonical-observations.preview.json").read_text(encoding="utf-8"))
        wrong_period["data"][1]["period_type"] = "day"
        wrong_period["data"][1]["period"] = "2026-09-28"
        dump(preview / "canonical-observations.preview.json", wrong_period)
        period_processed = temp / "processed-period"
        output_period, report_period = build_production(preview, period_processed, POLICY)
        assert output_period["record_count"] == 1
        assert any(x["indicator_id"] == "bank-funding-growth-ytd" and x["action"] == "hold-period-type" for x in report_period["held"])

        print("Phase 4.2I.3 banking production policy tests passed")
    finally:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    main()
