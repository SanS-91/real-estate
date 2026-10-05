from pathlib import Path
import importlib
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CASES = [
    (
        "collectors.baochinhphu_policy_rates",
        "discover_baochinhphu_policy_rates_url",
        "parse_baochinhphu_policy_rates",
        "baochinhphu_policy_rates",
        "https://baochinhphu.vn/",
        "gov-vietnam-baochinhphu",
    ),
    (
        "collectors.vietnamplus_policy_rates",
        "discover_vietnamplus_policy_rates_url",
        "parse_vietnamplus_policy_rates",
        "vietnamplus_policy_rates",
        "https://www.vietnamplus.vn/ngan-hang-tag708050.vnp",
        "vna-vietnamplus",
    ),
    (
        "collectors.thoibaonganhang_policy_rates",
        "discover_thoibaonganhang_policy_rates_url",
        "parse_thoibaonganhang_policy_rates",
        "thoibaonganhang_policy_rates",
        "https://thoibaonganhang.vn/ngan-hang",
        "banking-times-vn",
    ),
]


def test_policy_news_parsers_and_discovery():
    expected = {
        "policy-refinancing-rate": 4.5,
        "policy-rediscount-rate": 3.0,
        "policy-overnight-lending-rate": 5.0,
    }
    for modname, discover_name, parse_name, stem, landing, source_id in CASES:
        mod = importlib.import_module(modname)
        listing = (ROOT / f"tests/fixtures/{stem}_listing_sample.html").read_text(encoding="utf-8")
        detail = (ROOT / f"tests/fixtures/{stem}_sample.html").read_text(encoding="utf-8")
        url = getattr(mod, discover_name)(listing, landing)
        assert url and url.startswith("https://")
        rows = getattr(mod, parse_name)(detail, url, "2026-10-05T00:00:00Z")
        assert len(rows) == 3
        assert {r["indicator_id"]: r["value"] for r in rows} == expected
        assert {r["period"] for r in rows} == {"2023-06-19"}
        assert {r["period_type"] for r in rows} == {"date"}
        assert {r["source_id"] for r in rows} == {source_id}
        assert {r["evidence_status"] for r in rows} == {"reported"}


def test_forecast_is_not_mistaken_for_policy_event():
    from collectors.policy_news_common import discover_policy_news_url
    html = '''<html><body><article><a href="/forecast.html">UOB dự báo NHNN giữ nguyên lãi suất tái cấp vốn 4,5% trong năm 2026</a></article></body></html>'''
    assert discover_policy_news_url(html, "https://thoibaonganhang.vn/ngan-hang", "thoibaonganhang.vn") is None


def test_policy_pool_uses_lightweight_news_sources_not_large_archive():
    pools = json.loads((ROOT / "config/source_pools.json").read_text(encoding="utf-8"))["pools"]
    policy = next(p for p in pools if p["id"] == "policy-rates")
    assert policy["fallback_source_ids"] == [
        "gov-vietnam-baochinhphu",
        "vna-vietnamplus",
        "banking-times-vn",
    ]
    assert policy["min_independent_sources_for_corroborated"] == 2

    live = json.loads((ROOT / "config/live_sources.json").read_text(encoding="utf-8"))["sources"]
    archive = next(x for x in live if x["key"] == "sbv-policy-archive")
    assert archive["enabled"] is False
    for key in ["baochinhphu-policy-rates", "vietnamplus-policy-rates", "banking-times-policy-rates"]:
        src = next(x for x in live if x["key"] == key)
        assert src["enabled"] is True
        assert src["max_bytes"] <= 3_000_000
        assert src["schedule_class"] == "event-driven-policy-news-search"
        assert src["fallback_on_parse_shortfall"] is True


def test_three_source_fixture_run_is_ready_corroborated():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "candidate"
        cmd = [
            sys.executable,
            str(ROOT / "scripts/candidate_pipeline.py"),
            "--fixture-mode",
            "--replace-history",
            "--output-root",
            str(out),
            "--source",
            "baochinhphu-policy-rates",
            "--source",
            "vietnamplus-policy-rates",
            "--source",
            "banking-times-policy-rates",
        ]
        cp = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if cp.returncode != 0:
            print(cp.stdout)
            print(cp.stderr)
            raise SystemExit(cp.returncode)
        report = json.loads((out / "run-report.json").read_text(encoding="utf-8"))
        readiness = json.loads((out / "publish-readiness.json").read_text(encoding="utf-8"))
        assert report["new_observations"] == 9
        by = {x["indicator_id"]: x for x in readiness["data"]}
        for iid in ["policy-refinancing-rate", "policy-rediscount-rate", "policy-overnight-lending-rate"]:
            assert by[iid]["status"] == "ready-corroborated"
            assert len(by[iid]["independent_sources"]) == 3
            assert by[iid]["latest_business_period"] == "2023-06-19"


def test_workflow_exposes_news_search_gate():
    wf = (ROOT / ".github/workflows/macro-candidate.yml").read_text(encoding="utf-8")
    assert "policy-news-search" in wf
    block = wf.split('elif [ "$SOURCE" = "policy-news-search" ]; then', 1)[1].split('elif [ "$SOURCE" = "policy-liquidity-discovery" ]; then', 1)[0]
    assert "--source baochinhphu-policy-rates" in block
    assert "--source vietnamplus-policy-rates" in block
    assert "--source banking-times-policy-rates" in block
    assert "sbv-policy-archive" not in block
    pipeline = (ROOT / "scripts/candidate_pipeline.py").read_text(encoding="utf-8")
    assert "detail_fallback_used" in pipeline


if __name__ == "__main__":
    test_policy_news_parsers_and_discovery()
    test_forecast_is_not_mistaken_for_policy_event()
    test_policy_pool_uses_lightweight_news_sources_not_large_archive()
    test_three_source_fixture_run_is_ready_corroborated()
    test_workflow_exposes_news_search_gate()
    print("Phase 4.2K.2 policy news search tests passed")
