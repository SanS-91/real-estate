from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from candidate_pipeline import build_publish_readiness
from collectors.nso_banking_activity import (
    discover_nso_banking_activity_url,
    parse_nso_banking_activity,
)

NOW = "2026-10-05T02:00:00+00:00"


def main():
    fixture = (ROOT / "tests/fixtures/nso_banking_activity_sample.html").read_text(encoding="utf-8")
    rows = parse_nso_banking_activity(fixture, "https://www.nso.gov.vn/example/", NOW)
    d = {x["indicator_id"]: x for x in rows}
    assert set(d) == {"bank-funding-growth-ytd", "credit-growth-ytd"}
    assert d["bank-funding-growth-ytd"]["value"] == 9.78
    assert d["credit-growth-ytd"]["value"] == 10.89
    assert d["credit-growth-ytd"]["period"] == "2026-09"
    assert d["credit-growth-ytd"]["data_date"] == "2026-09-28"
    assert d["credit-growth-ytd"]["published_at"] == "2026-10-03"
    assert all(x["evidence_status"] == "verified" for x in rows)

    listing = """
      <a href='/tin-tuc-thong-ke/2026/10/thong-cao-bao-chi-ve-tinh-hinh-gia-thang-chin/'>Thông cáo báo chí về tình hình giá tháng Chín</a>
      <a href='/bai-top/2026/07/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-ii-va-sau-thang-dau-nam-2026/'>Báo cáo tình hình kinh tế – xã hội quý II và sáu tháng đầu năm 2026</a>
      <a href='/bai-top/2026/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/'>Báo cáo tình hình kinh tế – xã hội quý III và 9 tháng năm 2026</a>
    """
    url = discover_nso_banking_activity_url(listing, "https://www.nso.gov.vn/tin-tuc-thong-ke/")
    assert url.endswith("/2026/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/")

    for i, row in enumerate(rows, start=1):
        row["id"] = f"fixture-{i}"
    readiness = build_publish_readiness(rows, NOW)
    states = {x["indicator_id"]: x for x in readiness["data"]}
    assert states["credit-growth-ytd"]["status"] == "ready-canonical"
    assert states["bank-funding-growth-ytd"]["status"] == "ready-canonical"

    fmap = json.loads((ROOT / "config/frontend_indicator_map.json").read_text(encoding="utf-8"))["mappings"]
    assert fmap["credit-growth-ytd"]["status"] == "compatible"
    assert fmap["bank-funding-growth-ytd"]["status"] == "compatible"

    print("Phase 4.2I.1 NSO banking-activity tests passed")


if __name__ == "__main__":
    main()
