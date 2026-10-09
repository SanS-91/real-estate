"""Fail-closed Muaban source checks; no external HTTP required."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from market_muaban_verified_listings import (
    safe_url, discover, parse_detail, evaluate, scan, fingerprint,
)

NOW = datetime(2026, 10, 9, 13, 0, tzinfo=timezone.utc)
BASE = "https://muaban.net/bat-dong-san/"
CATALOG = BASE + "ban-can-ho-chung-cu-du-an-akari-city-quan-binh-tan-ho-chi-minh"
URL = CATALOG + "/chinh-chu-ban-akari-can-ho-id71299999"


def html(project="Akari City", start="05/10/2026", expiry="15/10/2026",
         price="4,4 tỷ", area="78 m²", ident="71299999",
         title="BÁN CĂN HỘ AKARI CITY 2PN", updated="1 giờ trước"):
    return f"""<html><body><main>
      <h1>{title}</h1>
      {price}
      Phường An Lạc, TP.HCM
      Cập nhật: {updated}
      Thông tin chi tiết
      Giá bán: {price}
      Thông tin cơ bản
      Loại hình căn hộ: Chung cư
      Dự án: {project}
      Diện tích sử dụng: {area}
      Thông tin dự án
      {project}
      Ngày bắt đầu {start}
      Ngày hết hạn {expiry}
      Mã tin {ident}
      </main></body></html>"""


def cfg():
    return {"targets": [{"project_id": "akari-city",
                         "publisher_project_name": "Akari City",
                         "url": CATALOG}]}


def get(url, listing):
    if listing:
        return html(), "reachable"
    return f'<a href="{URL}">Akari City 2PN</a><a href="{URL}">dup</a>', "reachable"


class MuabanListingTests(unittest.TestCase):
    def test_url_catalog_and_detail_bounded(self):
        self.assertEqual(discover(f'<a href="{URL}">ad</a>'*3, CATALOG), [URL])
        self.assertIsNone(safe_url("https://muaban.net.evil.com/bat-dong-san/ban-can-ho/a-id12", True))
        self.assertIsNone(safe_url(URL + "?redirect=evil", True))
        self.assertIsNone(safe_url(BASE + "cho-thue-can-ho-chung-cu-abc/id71299999", True))
        self.assertIsNone(safe_url(CATALOG, True))

    def test_exact_publisher_price_area_and_expiry(self):
        row, decision = parse_detail(html(), URL, "Akari City", "akari-city", NOW)
        self.assertEqual(decision, "qualified-unexpired-listing")
        self.assertEqual(row["listed_area_sqm"], 78)
        self.assertEqual(row["listing_price_vnd"], 4_400_000_000)
        self.assertEqual(row["value_vnd_per_m2"], round(4_400_000_000/78))
        self.assertEqual(row["source_listed_date"], "2026-10-05")
        self.assertEqual(row["source_expiration_date"], "2026-10-15")
        self.assertEqual(row["source_date_basis"], "publisher-listing-start-not-update")
        self.assertNotIn("average_asp", row)

    def test_expiry_outranks_dynamic_updated_badge(self):
        row, decision = parse_detail(html(start="10/08/2026", expiry="24/08/2026",
                                          updated="1 giờ trước"), URL,
                                     "Akari City", "akari-city", NOW)
        self.assertIsNone(row)
        self.assertEqual(decision, "publisher-expired")

    def test_expiry_project_rental_and_price_safety(self):
        samples = [
            (html(project="Vinhomes Grand Park"), "project-not-explicit"),
            (html(title="CHO THUÊ CĂN HỘ AKARI CITY"), "non-apartment-or-rental"),
            (html(price="Thỏa thuận"), "missing-numeric-total-sale-price"),
            (html(expiry="01/09/2026", updated="Hôm nay"), "publisher-expired"),
            (html(area="20 m²"), "invalid-area"),
            (html(ident="70111111"), "listing-id-mismatch"),
            (html(expiry="20/10/2026", start="20/11/2026"), "incomplete-or-conflicting-validity"),
        ]
        for example, expected in samples:
            with self.subTest(expected=expected):
                _, decision = parse_detail(example, URL, "Akari City", "akari-city", NOW)
                self.assertEqual(decision, expected)

    def test_two_independent_hosted_checks_and_no_project_aggregate(self):
        prod, state, health, _ = scan(cfg(), {"data":[]}, {}, get, NOW, "run-1")
        self.assertEqual(health["valid_unexpired_project_ads"], 1)
        self.assertEqual(prod["record_count"], 0)
        _, state, _, _ = scan(cfg(), prod, state, get, NOW+timedelta(minutes=30), "run-2")
        self.assertEqual(len(state["listings"][0]["checks"]), 2)
        prod, state, health, _ = scan(
            cfg(), prod, state, get, NOW+timedelta(hours=2), "run-3")
        self.assertEqual(prod["record_count"], 1)
        self.assertEqual(health["published_current_individual_listings"], 1)
        self.assertEqual(prod["data"][0]["verification_run_ids"], ["run-2","run-3"])
        self.assertTrue(health["no_project_asp_or_range"])
        self.assertNotIn("price_range", prod["data"][0])

    def test_pr_never_self_publishes_even_with_previous_proof(self):
        _, state, _, _ = scan(cfg(), {"data":[]}, {}, get, NOW, "main-check")
        prod, same, health, decisions = scan(
            cfg(), {"data":[]}, state, get, NOW+timedelta(hours=2),
            "pr-check", publish=False)
        self.assertEqual(prod["data"], [])
        self.assertEqual(same, state)
        self.assertFalse(health["publication_enabled"])
        self.assertTrue(all(x["decision"]=="pr-diagnostic-only" for x in decisions))


if __name__ == "__main__":
    unittest.main()
