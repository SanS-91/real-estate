import sys
import unittest
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import market_onehousing_peer_monthly as peer

NOW=datetime(2026,10,10,3,0,tzinfo=timezone.utc)
CFG=peer.provider.load(peer.CONFIG)
TARGET=CFG["targets"][0]
EMPTY={"schema_version":1,"record_count":0,"data":[]}
def reading(period="2026-09",price=122_580_000):
    return {"period":period,"value_vnd_per_m2":price,
            "range_low_vnd_per_m2":100_210_000,
            "range_high_vnd_per_m2":204_190_000}
def payload(obs=None, target=TARGET):
    return {target["id"]:({"status":"publisher-month-parsed","source_period":(obs or reading())["period"],
                             "http_status":200},obs or reading())}

class PeerMonthly(unittest.TestCase):
    def test_config_pinned_and_separate(self):
        self.assertEqual(len(CFG["targets"]),3)
        self.assertEqual(len({t["id"] for t in CFG["targets"]}),3)
        for target in CFG["targets"]:
            self.assertTrue(peer.safe_target(target),target)
            self.assertEqual(target["source_id"],"onehousing-vn")
        self.assertFalse(peer.safe_target({**TARGET,"url":"https://other.example.com/offer"}))
        self.assertFalse(peer.safe_target({**TARGET,"url":TARGET["url"]+"?bypass=1"}))
        self.assertFalse(peer.safe_target({**TARGET,"source_id":"rever-vn"}))

    def test_two_distinct_hour_spaced_runs(self):
        s,h,health=peer.evaluate(CFG,{},EMPTY,payload(),NOW,"run-100")
        self.assertEqual(h["record_count"],0)
        self.assertEqual(health["checks"][0]["status"],"awaiting-independent-hosted-check")
        self.assertEqual(health["exact_publisher_months_parsed"],1)
        s,h,health=peer.evaluate(CFG,s,h,payload(),NOW+timedelta(hours=2),"run-100")
        self.assertEqual(h["record_count"],0,"same hosted run cannot double-verify")
        s,h,health=peer.evaluate(CFG,s,h,payload(),NOW+timedelta(minutes=30),"run-101")
        self.assertEqual(h["record_count"],0,"different run too soon")
        s,h,health=peer.evaluate(CFG,s,h,payload(),NOW+timedelta(hours=2),"run-102")
        self.assertEqual(h["record_count"],1)
        row=h["data"][0]
        self.assertEqual(row["period"],"2026-09")
        self.assertEqual(row["value_vnd_per_m2"],122_580_000)
        self.assertEqual(row["scope_type"],"separate-hcm-peer-comparable")
        self.assertEqual(row["review_status"],"automated-two-hosted-checks")
        self.assertNotIn("project_id",row)
        self.assertIn("run-100",row["verification_run_ids"])
        s,h,health=peer.evaluate(CFG,s,h,payload(),NOW+timedelta(hours=3),"run-103")
        self.assertEqual(h["record_count"],1)
        self.assertEqual(health["checks"][0]["status"],"published-period-unchanged")

    def test_same_month_price_conflict_stays_blocked(self):
        s,h,_=peer.evaluate(CFG,{},EMPTY,payload(),NOW,"run-1")
        s,h,status=peer.evaluate(CFG,s,h,payload(reading(price=125_000_000)),
                                  NOW+timedelta(hours=2),"run-2")
        self.assertEqual(h["record_count"],0)
        self.assertEqual(status["checks"][0]["status"],"candidate-period-price-conflict")
        for r in ["run-3","run-4"]:
            s,h,status=peer.evaluate(CFG,s,h,payload(),NOW+timedelta(hours=4),r)
        self.assertEqual(h["record_count"],0)
        self.assertEqual(status["checks"][0]["status"],"candidate-period-price-conflict")

    def test_future_or_aged_periods_not_verifiable(self):
        self.assertFalse(peer.eligible_observation(TARGET,reading("2026-11"),NOW.date()))
        self.assertFalse(peer.eligible_observation(TARGET,reading("2026-05"),NOW.date()))
        self.assertFalse(peer.eligible_observation(TARGET,reading("2026-13"),NOW.date()))
        self.assertFalse(peer.eligible_observation(TARGET,reading(price=1),NOW.date()))
        self.assertFalse(peer.eligible_observation(TARGET,reading(price=250_000_000),NOW.date()))

    def test_abnormal_increment_rejected(self):
        s,h,_=peer.evaluate(CFG,{},EMPTY,payload(),NOW,"run-a")
        s,h,_=peer.evaluate(CFG,s,h,payload(),NOW+timedelta(hours=2),"run-b")
        self.assertEqual(h["record_count"],1)
        s,h,status=peer.evaluate(CFG,s,h,payload(reading("2026-10",170_000_000)),
                                  NOW+timedelta(hours=3),"run-c")
        self.assertEqual(h["record_count"],1)
        self.assertEqual(status["checks"][0]["status"],"price-change-outlier-review")
        s,h,status=peer.evaluate(CFG,s,h,payload(reading("2026-09",126_000_000)),
                                  NOW+timedelta(hours=4),"run-d")
        self.assertEqual(status["checks"][0]["status"],"published-period-conflict")
        self.assertEqual(h["record_count"],1)

    def test_official_html_exact_name(self):
        def markup(name):
            return ("<html><body><h1>Đặc điểm dự án</h1>"
                    f"Căn hộ chung cư dự án {name} tháng 9/2026 "
                    "Biến động giá Đơn giá phổ biến Mức giá/ mét vuông "
                    "xuất hiện nhiều nhất trong khoảng giá "
                    "122.58 triệu/m² 0% Khoảng giá: 100.21 - 204.19 triệu "
                    "Giá thuê phổ biến Tin nổi bật</body></html>")
        good=peer.provider.onehousing_monthly(peer.provider.plain_text(markup("Masteri Thảo Điền")),
                                                NOW.date(),TARGET["publisher_project_name"])
        wrong=peer.provider.onehousing_monthly(peer.provider.plain_text(markup("Estella Heights")),
                                                 NOW.date(),TARGET["publisher_project_name"])
        self.assertEqual(good["period"],"2026-09")
        self.assertIsNone(wrong)

    def test_blocked_page_does_not_fallback(self):
        with patch.object(peer.provider,"fetch_html",return_value=({"status":"blocked","http_status":403},None)) as f:
            summary,record=peer.publisher_probe(TARGET,None,NOW.date())
        self.assertEqual(f.call_count,1)
        self.assertIsNone(record)
        self.assertEqual(summary["status"],"blocked")

    def test_no_record_fabricated_for_missing_publisher_evidence(self):
        actual={TARGET["id"]:({"status":"unverifiable-project-month","http_status":200},None)}
        s,h,health=peer.evaluate(CFG,{},EMPTY,actual,NOW,"run")
        self.assertEqual(h["record_count"],0)
        self.assertEqual(health["new_verified_months"],0)
        self.assertNotIn("122580000",str(health))
        self.assertNotIn("value_vnd_per_m2",str(health))

if __name__=="__main__":
    unittest.main()
