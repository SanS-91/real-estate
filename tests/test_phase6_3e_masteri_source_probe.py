"""Fail-closed publisher mirror diagnosis; no price or period fabricated."""
import unittest, sys
from pathlib import Path
from datetime import date
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import market_alternative_auto_probe as source
import market_onehousing_source_probe as monitor

URL="https://beta.onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Masteri-Centre-Point.53"
ALT="https://onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Masteri-Centre-Point.53"
NOW=date(2026,10,10)
TARGET={"source_id":"onehousing-vn","target_id":monitor.TARGET_ID,
        "project_id":"vinhomes-grand-park",
        "mode":"monthly-price-candidate","period_type":"month",
        "publisher_project_name":"Masteri Centre Point","url":URL,
        "fallback_urls":[ALT]}
OLDER="""<html><body><h1>Masteri Centre Point</h1>
Căn hộ chung cư dự án Masteri Centre Point tháng 8/2026
Đơn giá phổ biến Mức giá/ mét vuông xuất hiện nhiều nhất trong khoảng giá
72.89 triệu/m² 0% Khoảng giá: 54.32 - 224.87 triệu
Giá thuê phổ biến Giá thuê căn hộ theo tháng
Tin tức chính sách, tiện ích nội khu và thông tin dự án
</body></html>"""
WRONG=OLDER.replace("Masteri Centre Point","Lumière Boulevard")
BLOCKED={"status":"blocked","http_status":403,"final_host":"beta.onehousing.vn"}
GOOD={"status":"reachable","http_status":200,"final_host":"onehousing.vn"}
BETA={"status":"reachable","http_status":200,"final_host":"beta.onehousing.vn"}

class OfficialMirrorDiagnosis(unittest.TestCase):
    def test_exact_project_bounded_period(self):
        parsed=source.onehousing_monthly(source.plain_text(OLDER),NOW,"Masteri Centre Point")
        self.assertEqual(parsed["period"],"2026-08")
        self.assertIsNone(source.onehousing_monthly(source.plain_text(WRONG),NOW,"Masteri Centre Point"))

    def test_forbidden_block_does_not_use_mirror(self):
        with patch.object(source,"fetch_html",return_value=(BLOCKED,None)) as fetch:
            result,html=source.fetch_with_publisher_fallback(TARGET,None)
            self.assertIsNone(html)
            self.assertEqual(fetch.call_count,1)
            self.assertEqual(len(result["source_variants"]),1)
            self.assertEqual(result["source_variants"][0]["http_status"],403)

    def test_official_fallback_returns_older_period_not_fake_current(self):
        def fetch(t,_):
            return (BETA,WRONG) if t["url"]==URL else (GOOD,OLDER)
        with patch.object(source,"fetch_html",side_effect=fetch) as fetch_mock:
            state,html=source.fetch_with_publisher_fallback(TARGET,None)
            self.assertEqual(fetch_mock.call_count,2)
        self.assertEqual(state["checked_url"],ALT)
        self.assertTrue(state["fallback_used"])
        self.assertEqual(len(state["source_variants"]),2)
        self.assertFalse(state["source_variants"][0]["verified_source_scope"])
        self.assertTrue(state["source_variants"][1]["verified_source_scope"])
        self.assertEqual(state["source_variants"][1]["verified_source_period"],"2026-08")
        bas=next(x for x in source.load(monitor.BASE)["data"] if x["id"]=="onehousing-masteri-centre-point-apartment-2026-09")
        result,candidate=source.classify(TARGET,html,bas,NOW)
        self.assertEqual(result,"older-period-no-candidate")
        self.assertIsNone(candidate)

    def test_wrong_project_or_missing_metric_cannot_be_published(self):
        with patch.object(source,"fetch_html",side_effect=[(BETA,WRONG),(GOOD,WRONG)]):
            state,html=source.fetch_with_publisher_fallback(TARGET,None)
        self.assertNotIn("fallback_used",state)
        self.assertEqual(state["checked_url"],URL)
        self.assertFalse(any(r["verified_source_scope"] for r in state["source_variants"]))
        self.assertIsNone(source.onehousing_monthly(source.plain_text(html),NOW,"Masteri Centre Point"))

    def test_invalid_mirror_path_is_never_fetched(self):
        bad={**TARGET,"fallback_urls":["https://onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Lumiere-Boulevard.34",
                                      "https://bad-onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Masteri-Centre-Point.53",
                                      ALT+"?bypass=1"]}
        with patch.object(source,"fetch_html",return_value=(BETA,WRONG)) as fetch:
            result,html=source.fetch_with_publisher_fallback(bad,None)
            self.assertEqual(fetch.call_count,1)
            self.assertEqual(len(result["source_variants"]),1)

    def test_monitor_never_writes_data_or_candidate(self):
        def fake(target,session):
            return ({"status":"reachable","http_status":200,"checked_url":ALT,
                     "source_variants":[{"host":"onehousing.vn","verified_source_period":"2026-08"}]},OLDER)
        payload=monitor.inspect(fetcher=fake,now=NOW)
        self.assertTrue(payload["source_checks_only"])
        self.assertFalse(payload["production_written"])
        self.assertFalse(payload["candidate_written"])
        self.assertEqual(payload["source_status"],"older-period-no-candidate")
        self.assertEqual(payload["reviewed_baseline_period"],"2026-09")
        self.assertEqual(payload["latest_published_period"],"2026-09")
        self.assertNotIn("value_vnd_per_m2",str(payload))

if __name__=="__main__":
    unittest.main()
