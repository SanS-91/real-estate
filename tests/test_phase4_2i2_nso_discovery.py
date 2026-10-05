from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import candidate_pipeline
from collectors.base import FetchResult

NOW = "2026-10-05T07:00:00+00:00"


def fake_result(url: str, text: str) -> FetchResult:
    return FetchResult(
        url=url,
        status_code=200,
        text=text,
        fetched_at=NOW,
        content_hash="fixture-hash",
        content_type="text/html",
        elapsed_ms=1,
    )


def main():
    cfg = json.loads((ROOT / "config/live_sources.json").read_text(encoding="utf-8"))
    source = next(x for x in cfg["sources"] if x["key"] == "nso-banking-activity")
    assert source.get("landing_urls") == [
        "https://www.nso.gov.vn/bai-top/",
        "https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/",
        "https://www.nso.gov.vn/tin-tuc-thong-ke/",
    ]

    detail_url = "https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/10/thong-cao-bao-chi-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/"
    pages = {
        # Preferred listing is reachable but does not expose the target in this regression case.
        source["landing_urls"][0]: "<html><a href='/unrelated/'>Unrelated</a></html>",
        # Fallback listing exposes the official press release.
        source["landing_urls"][1]: f"<html><a href='{detail_url}'>Thông cáo báo chí tình hình kinh tế – xã hội quý III và 9 tháng năm 2026</a></html>",
        detail_url: (ROOT / "tests/fixtures/nso_banking_activity_sample.html").read_text(encoding="utf-8"),
    }

    original_fetch = candidate_pipeline.fetch_html
    run_id = "phase4_2i2-fixture"
    raw_dir = ROOT / "data/raw/live/nso-banking-activity" / run_id
    try:
        def fake_fetch(url, **kwargs):
            if url not in pages:
                raise AssertionError(f"Unexpected URL {url}")
            return fake_result(url, pages[url])

        candidate_pipeline.fetch_html = fake_fetch
        obs, research, health = candidate_pipeline.fetch_source(source, run_id, fixture_mode=False)
        by_id = {x["indicator_id"]: x for x in obs}
        assert not research
        assert set(by_id) == {"credit-growth-ytd", "bank-funding-growth-ytd"}
        assert by_id["credit-growth-ytd"]["value"] == 10.89
        assert by_id["bank-funding-growth-ytd"]["value"] == 9.78
        assert health["target_url"] == detail_url
        attempts = health["landing"]["attempts"]
        assert len(attempts) == 2
        assert attempts[0]["discovered_target_url"] is None
        assert attempts[1]["discovered_target_url"] == detail_url
    finally:
        candidate_pipeline.fetch_html = original_fetch
        shutil.rmtree(raw_dir, ignore_errors=True)

    # Frontend registry exists now, but I.2 remains candidate/review only.
    fmap = json.loads((ROOT / "config/frontend_indicator_map.json").read_text(encoding="utf-8"))["mappings"]
    assert fmap["bank-funding-growth-ytd"]["frontend_indicator_id"] == "bank-funding-growth-ytd"
    assert fmap["bank-funding-growth-ytd"]["status"] == "compatible"
    prod = json.loads((ROOT / "config/production_promotion_policy.json").read_text(encoding="utf-8"))
    assert "credit-growth-ytd" not in prod["allowed_indicators"]
    assert "bank-funding-growth-ytd" not in prod["allowed_indicators"]

    print("Phase 4.2I.2 NSO multi-landing discovery tests passed")


if __name__ == "__main__":
    main()
