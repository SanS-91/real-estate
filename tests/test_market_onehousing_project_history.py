"""4I.3 parent-price history must remain true source-specific, idempotent and gated."""
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from market_onehousing_project_history import (
    monitored_pairs, baseline_row, evaluate, run, series_key,
)
import market_alternative_auto_probe as source

URL = "https://onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Vinhomes-Grand-Park.1012"
TARGET = {
    "target_id": "onehousing-vinhomes-grand-park-apartment",
    "baseline_id": "onehousing-vinhomes-grand-park-apartment-2026-10",
    "source_id": "onehousing-vn", "project_id": "vinhomes-grand-park",
    "url": URL, "mode": "monthly-price-candidate",
}
BASE = {
    "id": TARGET["baseline_id"], "project_id": "vinhomes-grand-park",
    "source_id": "onehousing-vn", "source_url": URL,
    "asset_type": "apartment", "metric_type": "popular-asking-price-per-sqm",
    "period_type": "month", "period": "2026-10",
    "review_date": "2026-10-09", "value_vnd_per_m2": 54470000,
    "range_low_vnd_per_m2": 36810000, "range_high_vnd_per_m2": 331190000,
    "evidence": {
        "period": "Căn hộ chung cư dự án Vinhomes Grand Park tháng 10/2026",
        "metric": "Đơn giá phổ biến | 54.47 triệu/m²",
        "range": "Khoảng giá: 36.81 - 331.19 triệu",
    }
}
HTML = """<html><body><section>Biến động giá
Căn hộ chung cư dự án Vinhomes Grand Park tháng 11/2026
Đơn giá phổ biến Mức giá/ mét vuông xuất hiện nhiều nhất trong khoảng giá
55.47 triệu/m² 0% Khoảng giá: 37.81 - 332.19 triệu
Giá thuê phổ biến Tiện ích nội khu</section></body></html>"""
NOW = datetime(2026, 11, 7, 8, 0, tzinfo=timezone.utc)
ACCESS = {"status": "reachable", "http_status": 200, "final_host": "onehousing.vn"}
NOV = {"period": "2026-11", "value_vnd_per_m2": 55470000,
       "range_low_vnd_per_m2": 37810000, "range_high_vnd_per_m2": 332190000,
       "evidence": {"period":"November", "metric":"55.47", "range":"37.81-332.19"}}


class ParentHistoryTests(unittest.TestCase):
    def test_bootstrap_only_reviewed_configured_parent(self):
        pairs = monitored_pairs([BASE], [TARGET])
        self.assertEqual(len(pairs), 1)
        bootstrap = baseline_row(BASE)
        self.assertEqual(bootstrap["value_vnd_per_m2"], BASE["value_vnd_per_m2"])
        self.assertEqual(bootstrap["review_status"], "source-indexed-baseline")
        self.assertEqual(bootstrap["period"], "2026-10")
        self.assertNotIn("subproject_name", bootstrap)
        self.assertFalse(monitored_pairs([BASE], [{**TARGET, "project_id":"the-global-city"}]))
        self.assertFalse(monitored_pairs([BASE], [{**TARGET, "url":"https://onehousing.vn/blog/" }]))

    def test_parser_only_correct_project_month(self):
        text=source.plain_text(HTML)
        parsed=source.onehousing_monthly(text, NOW.date(), "Vinhomes Grand Park")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["period"], "2026-11")
        self.assertEqual(parsed["value_vnd_per_m2"], NOV["value_vnd_per_m2"])
        self.assertIsNone(source.onehousing_monthly(text, NOW.date(), "Akari City"))

    def test_no_premature_publish_and_two_hours_and_idempotence(self):
        base=baseline_row(BASE)
        a, v, status=evaluate([base], [], BASE, TARGET, NOV, ACCESS, NOW, "1")
        self.assertIsNone(v)
        self.assertEqual(status,"need-two-consecutive-source-verifications")
        b, v, status=evaluate([base], a, BASE, TARGET, NOV, ACCESS, NOW+timedelta(minutes=30), "2")
        self.assertIsNone(v)
        self.assertEqual(status,"source-checks-under-one-hour")
        c, v, status=evaluate([base], b, BASE, TARGET, NOV, ACCESS, NOW+timedelta(hours=2), "3")
        self.assertEqual(status,"verified-new-publisher-month")
        self.assertEqual(v["source_record_id"], BASE["id"])
        self.assertEqual(v["review_status"],"automated-source-verified")
        self.assertEqual(v["verification_run_ids"],["2","3"])
        self.assertIsNone(v.get("subproject_name"))
        d, again, status=evaluate([base,v], c, BASE, TARGET, NOV, ACCESS, NOW+timedelta(hours=3), "4")
        self.assertIsNone(again)
        self.assertEqual(status, "already-in-source-history")

    def test_conflicts_bad_host_and_outlier_fail_closed(self):
        base=baseline_row(BASE)
        a, _, _=evaluate([base], [], BASE, TARGET, NOV, ACCESS, NOW, "1")
        _, x, status=evaluate([base], a, BASE, TARGET,
             {**NOV, "value_vnd_per_m2": 56000000}, ACCESS, NOW+timedelta(hours=2), "2")
        self.assertIsNone(x)
        self.assertEqual(status, "need-two-consecutive-source-verifications")
        bad={**NOV, "value_vnd_per_m2": 95000000}
        a, _, _=evaluate([base], [], BASE, TARGET, bad, ACCESS, NOW, "1")
        _, x, status=evaluate([base], a, BASE, TARGET, bad, ACCESS, NOW+timedelta(hours=2), "2")
        self.assertEqual(status, "price-jump-manual-review")
        self.assertIsNone(x)
        _, x, status=evaluate([base], [], BASE, TARGET, NOV,
                 {**ACCESS,"http_status": 403}, NOW, "1")
        self.assertIsNone(x)

    def test_pipeline_reuses_existing_baseline_and_waits_for_new_month(self):
        payload,state,decisions=run([BASE], [TARGET], {"data":[]}, {}, NOW, "run1",
                 lambda t: (ACCESS, HTML))
        self.assertEqual(payload["record_count"],1)
        self.assertEqual(payload["data"][0]["period"],"2026-10")
        self.assertEqual(len(state["series"]),1)
        self.assertEqual(decisions[0]["decision"],"need-two-consecutive-source-verifications")
        updated,_,_=run([BASE], [TARGET], payload, state, NOW+timedelta(hours=2), "run2",
                 lambda t: (ACCESS, HTML))
        self.assertEqual(updated["record_count"],2)
        self.assertEqual(updated["data"][1]["period"],"2026-11")


if __name__ == "__main__":
    unittest.main()
