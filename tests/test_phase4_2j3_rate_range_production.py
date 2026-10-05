from pathlib import Path
import json, sys, tempfile, shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from promote_production import build_production

POLICY = ROOT / "config/production_promotion_policy.json"
FRONTEND = ROOT / "config/frontend_indicator_map.json"

RANGE_IDS = {
    "deposit-rate-vnd-6-12m-low": 6.5,
    "deposit-rate-vnd-6-12m-high": 8.0,
    "lending-rate-vnd-average-low": 8.4,
    "lending-rate-vnd-average-high": 10.7,
}

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    for iid in RANGE_IDS:
        cfg = policy["allowed_indicators"][iid]
        assert cfg["required_readiness_statuses"] == ["ready-corroborated"]
        assert cfg["required_evidence_status"] == "corroborated"
        assert cfg["required_min_independent_sources"] == 2
        assert set(cfg["allowed_sources"]) == {"vnba", "vna-vietnamplus"}
    assert "priority-short-term-lending-rate-vnd" not in policy["allowed_indicators"]

    fmap = json.loads(FRONTEND.read_text(encoding="utf-8"))["mappings"]
    assert fmap["deposit-rate-vnd-6-12m-low"]["frontend_indicator_id"] == "deposit-rate-vnd-6-12m-range"
    assert fmap["deposit-rate-vnd-6-12m-high"]["frontend_indicator_id"] == "deposit-rate-vnd-6-12m-range"
    assert fmap["lending-rate-vnd-average-low"]["frontend_indicator_id"] == "lending-rate-vnd-average-range"
    assert fmap["lending-rate-vnd-average-high"]["frontend_indicator_id"] == "lending-rate-vnd-average-range"
    assert fmap["priority-short-term-lending-rate-vnd"]["frontend_indicator_id"] is None

    tmp = Path(tempfile.mkdtemp(prefix="phase4-2j3-"))
    try:
        preview = tmp / "preview"
        processed = tmp / "processed"
        canonical = []
        manifest = []
        for iid, value in RANGE_IDS.items():
            rid = f"vnba-{iid}-2026-08"
            canonical.append({
                "id": rid,
                "source_record_id": rid,
                "indicator_id": iid,
                "period": "2026-08",
                "period_type": "month",
                "data_date": "2026-08-01",
                "value": value,
                "unit": "percent-per-year",
                "source_id": "vnba",
                "source_url": "https://vnba.example/rates-aug-2026",
                "published_at": "2026-09-25",
                "fetched_at": "2026-10-05T00:00:00+00:00",
                "evidence_status": "corroborated",
                "corroboration_source_ids": ["vnba", "vna-vietnamplus"],
                "corroboration_observation_ids": [rid, f"vnp-{iid}-2026-08"],
                "corroboration_reason": "Two independent fallback sources agree.",
                "observation_status": "candidate",
                "preview_only": True
            })
            manifest.append({
                "indicator_id": iid,
                "readiness_status": "ready-corroborated",
                "action": "promote-canonical-preview",
                "selected_observation_id": rid
            })

        # The unresolved priority observation must remain blocked from production.
        priority_id = "priority-short-term-lending-rate-vnd"
        canonical.append({
            "id": "vnba-priority-2026-08",
            "source_record_id": "vnba-priority-2026-08",
            "indicator_id": priority_id,
            "period": "2026-08",
            "period_type": "month",
            "data_date": "2026-08-01",
            "value": 3.9,
            "unit": "percent-per-year",
            "source_id": "vnba",
            "source_url": "https://vnba.example/rates-aug-2026",
            "published_at": "2026-09-25",
            "fetched_at": "2026-10-05T00:00:00+00:00",
            "evidence_status": "reported",
            "observation_status": "candidate",
            "preview_only": True
        })
        manifest.append({
            "indicator_id": priority_id,
            "readiness_status": "evidence-only",
            "action": "hold-evidence",
            "selected_observation_id": "vnba-priority-2026-08"
        })

        dump(preview / "canonical-observations.preview.json", {
            "schema_version": 2,
            "generated_at": "2026-10-05T00:00:00+00:00",
            "record_count": len(canonical),
            "preview_only": True,
            "source_run_id": "j3-test",
            "data": canonical
        })
        dump(preview / "promotion-manifest.json", {
            "schema_version": 2,
            "generated_at": "2026-10-05T00:00:00+00:00",
            "production_write": False,
            "data": manifest
        })
        dump(preview / "preview-meta.json", {
            "schema_version": 1,
            "source_run_id": "j3-test"
        })

        out, report = build_production(preview, processed, POLICY)
        assert out["record_count"] == 4, out
        assert {r["indicator_id"] for r in out["data"]} == set(RANGE_IDS)
        assert all(r["evidence_status"] == "corroborated" for r in out["data"])
        assert all(set(r["corroboration_source_ids"]) == {"vnba", "vna-vietnamplus"} for r in out["data"])
        assert any(h["indicator_id"] == priority_id and h["action"] == "hold-not-allowlisted" for h in report["held"])

        macro_js = (ROOT / "assets/js/macro.js").read_text(encoding="utf-8")
        home_js = (ROOT / "assets/js/home.js").read_text(encoding="utf-8")
        charts_js = (ROOT / "assets/js/charts.js").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/macro-candidate.yml").read_text(encoding="utf-8")
        assert "customer-rates-production" in workflow
        assert "python scripts/candidate_pipeline.py --mode candidate --source vnba-customer-rates" in workflow
        assert "python scripts/candidate_pipeline.py --mode candidate --source vietnamplus-customer-rates" in workflow
        assert "buildProductionRateRanges" in macro_js
        assert "deposit-rate-vnd-6-12m-range" in macro_js
        assert "Average VND Lending Rate Range" in home_js
        assert "renderRangeSeries" in charts_js

        print("Phase 4.2J.3 customer-rate production policy/frontend range tests PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
