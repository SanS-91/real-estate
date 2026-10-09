"""Phase 4I.3: Lumière Riverside must be an independently sourced monitored PROJECT."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import market_alternative_auto_probe as source
from market_onehousing_project_history import monitored_pairs, baseline_row

def data(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class LumiereRiversideTests(unittest.TestCase):
    def setUp(self):
        self.projects = data("data/mock/market/projects.json")["data"]
        self.prices = data("data/mock/market/alternative-price-evidence.json")["data"]
        self.targets = data("config/market-alternative-auto-targets.json")["targets"]
        self.project = next(x for x in self.projects if x["id"] == "lumiere-riverside")
        self.price = next(x for x in self.prices if x["id"] == "onehousing-lumiere-riverside-apartment-2026-10")
        self.target = next(x for x in self.targets if x["target_id"] == "onehousing-lumiere-riverside-apartment")

    def test_exact_scope_source_and_registry_mapping(self):
        self.assertEqual(self.project["lead_developer_id"], "masterise")
        self.assertEqual(self.project["segment_ids"], ["apartment"])
        self.assertEqual(self.project["official_url"], "https://masterisehomes.com/lumiere-riverside/")
        self.assertEqual(self.price["project_id"], "lumiere-riverside")
        self.assertEqual(self.price["metric_type"], "popular-asking-price-per-sqm")
        self.assertEqual(self.price["source_publication_date"], None)
        self.assertEqual(self.target["url"], self.price["source_url"])
        self.assertEqual(self.target["baseline_id"], self.price["id"])
        self.assertEqual(self.target["publisher_project_name"], "Lumière Riverside")
        self.assertTrue(source.allowed_target(self.target))

    def test_onboarding_is_automated_from_real_indexed_reference(self):
        pairs = monitored_pairs([self.price], [self.target])
        self.assertEqual(len(pairs), 1)
        row = baseline_row(self.price)
        self.assertEqual(row["review_status"], "source-indexed-baseline")
        self.assertEqual(row["value_vnd_per_m2"], 178170000)
        self.assertEqual(row["series_key"], "onehousing-parent-lumiere-riverside-apartment-popular-asking")
        self.assertIsNone(row.get("subproject_name"))

    def test_explicit_source_values_match_full_month_and_price_range(self):
        text = ("Biến động giá " + self.price["evidence"]["period"]
                + " Đơn giá phổ biến Mức giá/ mét vuông xuất hiện nhiều nhất trong khoảng giá "
                + self.price["evidence"]["metric"] + " " + self.price["evidence"]["range"]
                + " Giá thuê phổ biến Tiện ích nội khu")
        parsed = source.onehousing_monthly(text, date(2026,10,9), "Lumière Riverside")
        self.assertEqual(parsed["period"], "2026-10")
        for col in ("value_vnd_per_m2", "range_low_vnd_per_m2", "range_high_vnd_per_m2"):
            self.assertEqual(parsed[col], self.price[col])
        self.assertIsNone(source.onehousing_monthly(text, date(2026,10,9), "Lumière Boulevard"))

    def test_source_is_not_a_project_asp_or_subproject_proxy(self):
        self.assertIsNone(self.price.get("average_asp"))
        self.assertFalse(self.target.get("subproject_name"))
        self.assertNotEqual(self.target["project_id"], "vinhomes-grand-park")
        self.assertFalse(any(r.get("subproject_name") == "Lumière Riverside" and
                             r.get("project_id") == "vinhomes-grand-park"
                             for r in self.prices))


if __name__ == "__main__":
    unittest.main()
