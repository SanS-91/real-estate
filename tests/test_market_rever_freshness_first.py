"""Phase 4I.5: discovery must maximize date-grounded candidates, not promote
catalog activity or cross-project prices. No internet needed for these tests.
"""
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from market_rever_project_listings import run, source_health

NOW = datetime(2026, 10, 9, 9, 0, tzinfo=timezone.utc)
ROOT = "https://rever.vn"
PROJECT = ROOT + "/s/the-privia/mua/can-ho"
DISTRICT = ROOT + "/s/binh-tan/mua/can-ho"
FRESH = ROOT + "/mua/can-ho-the-privia-huong-nam"
STALE = ROOT + "/mua/can-ho-the-privia-cu"
OTHER = ROOT + "/mua/can-ho-akari-city"


def detail(name="THE PRIVIA", updated="06/10/2026", lid="ATA199876"):
    return f"""<main><h1>Bán căn hộ {name} 55m²</h1>
      Mã nhà đất: {lid} Cập nhật: {updated}
      2.9 tỷ 52.73 triệu/m² 1 1 55m²
      Thông tin cơ bản Loại hình Căn hộ Phòng ngủ 1
      Dự án {name} Giá bán 2.9 tỷVND
    </main>"""


def fixture(url, listing=False):
    values = {
        PROJECT: f'<a href="{STALE}">Old Privia</a>',
        DISTRICT: f'<a href="{FRESH}">New Privia</a><a href="{OTHER}">Akari</a>'
                  f'<a href="{FRESH}">Duplicate</a>',
        FRESH: detail(),
        STALE: detail(updated="11/08/2024", lid="ATA199875"),
        OTHER: detail(name="Akari City", lid="ATA199877"),
    }
    return (values.get(url), "reachable" if url in values else "missing")


def configuration():
    return {"targets": [{
        "project_id": "the-privia",
        "publisher_project_name": "THE PRIVIA",
        "url": PROJECT,
        "discovery_urls": [DISTRICT],
    }]}


class FreshnessTests(unittest.TestCase):
    def test_regional_discovery_requires_exact_detail_project_and_date(self):
        first, state, report = run(configuration(), {"data": []}, {},
                                   fixture, NOW, "job-1")
        self.assertEqual(report["catalogs_checked"], 2)
        self.assertEqual(report["listing_urls_discovered"], 3)
        self.assertEqual(report["qualified_current_or_historical"], 2)
        self.assertEqual(report["recent_qualified"], 1)
        self.assertEqual(report["recent_30_days"], 1)
        self.assertEqual(report["accepted_new_individual_listings"], 0)
        self.assertIn("project-not-explicit", report["sources"][0]["reasons"])
        self.assertEqual(report["sources"][0]["latest_source_update_date"], "2026-10-06")
        self.assertEqual(first["data"], [])
        second, checks, report2 = run(configuration(), first, state,
                                      fixture, NOW + timedelta(hours=2), "job-2")
        self.assertEqual(report2["accepted_new_individual_listings"], 1)
        self.assertEqual(len(second["data"]), 1)
        self.assertEqual(second["data"][0]["project_id"], "the-privia")
        self.assertEqual(second["data"][0]["source_url"], FRESH)
        self.assertEqual(second["data"][0]["review_status"], "automated-two-hosted-checks")
        self.assertNotIn("average_asp", second["data"][0])
        snapshot = source_health(report2, checks, second)
        self.assertEqual(snapshot["source_updates_within_90_days"], 1)
        self.assertEqual(snapshot["published_current_individual_listings"], 1)
        self.assertEqual(snapshot["source_runs_seen"], 2)
        self.assertNotIn("listing_price_vnd", json.dumps(snapshot))
        self.assertNotIn("value_vnd_per_m2", json.dumps(snapshot))

    def test_pr_diagnostic_cannot_use_existing_hosted_check_to_publish(self):
        initial, state, _ = run(configuration(), {"data": []}, {},
                                fixture, NOW, "scheduled-main")
        preview, preview_state, report = run(
            configuration(), initial, state, fixture,
            NOW + timedelta(hours=3), "pull-request", publish=False)
        self.assertEqual(preview["data"], [])
        self.assertEqual(preview_state, state)
        self.assertFalse(report["publication_enabled"])
        self.assertEqual(report["accepted_new_individual_listings"], 0)
        self.assertTrue(all(row["decision"] == "pr-diagnostic-only"
                            for row in report["decisions"]))

    def test_invalid_regional_source_does_not_disable_project_catalog(self):
        cfg = configuration()
        cfg["targets"][0]["discovery_urls"] = ["https://malicious.test/s/apartments"]
        result, _, report = run(cfg, {"data": []}, {}, fixture, NOW, "run")
        self.assertEqual(report["sources"][0]["catalogs"][1]["access_status"],
                         "invalid-source-config")
        self.assertEqual(report["sources"][0]["qualified"], 1)
        self.assertFalse(result["data"])


if __name__ == "__main__":
    unittest.main()
