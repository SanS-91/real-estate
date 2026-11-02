"""Regression checks for market pulse source provenance and data gaps."""
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

script = Path(__file__).resolve().parents[1] / "scripts" / "build_market_daily_pulse.py"
spec = importlib.util.spec_from_file_location("pulse", script)
pulse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pulse)

NOW = datetime(2026, 11, 2, 8, 0, tzinfo=timezone.utc)
PROJECTS = [
    {"id": "izumi-city", "name": "Izumi City", "region_ids": ["dong-nai"]},
    {"id": "aqua-city", "name": "Aqua City", "region_ids": ["dong-nai"]},
    {"id": "the-privia", "name": "The Privia", "region_ids": ["hcmc"]},
]
OBS = [{"source_date": "2026-08-12", "period": "2026-Q2"}]
LISTINGS = [{"observation_date": "2026-10-09",
             "asking_price_low_vnd_per_m2": 50e6,
             "asking_price_high_vnd_per_m2": 60e6}]
ACTIVE = {"generated_at": "2026-11-01T00:00:00Z", "projects_monitored": 8,
          "projects_with_current_verified_unit_offers": 3, "current_verified_unit_ads": 9}
SOURCE = {"source_checked_at": "2026-10-30T00:00:00Z", "source_access": "blocked",
          "source_candidate_records": 0}


def article(title, days=1, explicit=None, url=None, source="vnexpress-real-estate"):
    return {"id": title, "title": title, "project_ids": explicit or [], "category": "market",
            "source_id": source, "url": url or "https://example.com/" + str(abs(hash(title))),
            "published_at": (NOW - timedelta(days=days)).isoformat()}


class PulseTests(unittest.TestCase):
    def build(self, articles):
        return pulse.build(PROJECTS, articles, OBS, LISTINGS, ACTIVE, SOURCE, now=NOW)

    def test_exact_title_only_inference(self):
        result = self.build([article("Izumi City công bố khu tiện ích"),
                             article("Thông tin Aqua City trong phần giới thiệu khác")])
        names = {r["project_id"] for r in result["article_index"]}
        self.assertEqual(names, {"izumi-city", "aqua-city"})
        self.assertEqual(result["inferred_headline_associations_30d"], 2)

    def test_does_not_match_partial_word_or_summary(self):
        row = article("Giới thiệu khu thủy sản Aqua Citywide")
        row["summary"] = "Aqua City có thông tin"
        result = self.build([row])
        self.assertEqual(result["article_index"], [])

    def test_explicit_id_keeps_provenance(self):
        result = self.build([article("Tiến độ được công bố", explicit=["the-privia"])])
        self.assertEqual(result["article_index"][0]["match_method"], "source-project-id")

    def test_never_publish_expired_future_or_demo(self):
        outdated = article("Izumi City ra mắt", days=31)
        future = article("Izumi City tương lai", days=-2)
        fake = article("Izumi City minh họa", source="demo-source")
        self.assertEqual(self.build([outdated, future, fake])["articles_screened_30d"], 0)

    def test_stale_price_is_not_live_price(self):
        quality = self.build([])["data_freshness"]
        self.assertTrue(quality["listing_aggregate"]["stale"])
        self.assertEqual(quality["listing_aggregate"]["observation_date"], "2026-10-09")
        self.assertEqual(quality["unit_listing_monitor"]["current_verified_unit_ads"], 9)
        self.assertEqual(quality["listing_collector"]["access_status"], "blocked")

    def test_url_required(self):
        bad = article("Izumi City")
        bad["url"] = "javascript:alert(1)"
        self.assertFalse(pulse.valid_article(bad, NOW))

    def test_duplicate_link_not_counted_twice(self):
        url = "https://publisher.example/one"
        rows = [article("Izumi City giai đoạn 1", url=url),
                article("Izumi City giai đoạn 1", url=url)]
        result = self.build(rows)
        project = next(x for x in result["project_updates"] if x["project_id"] == "izumi-city")
        self.assertEqual(project["matched_articles_30d"], 1)


if __name__ == "__main__":
    unittest.main()
