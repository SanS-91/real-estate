"""Phase 4H Nha Tot discovery: strict source isolation and no invented monthly price."""
import unittest
from unittest.mock import patch
from scripts import market_stable_listing_discovery as m

URL = "https://www.nhatot.com/mua-ban-can-ho-chung-cu-thanh-pho-thu-duc-tp-ho-chi-minh/135013161.htm"
INDEX = "https://www.nhatot.com/mua-ban-can-ho-chung-cu-thanh-pho-thu-duc-tp-ho-chi-minh"
PROJECTS = {"vinhomes-grand-park": "Vinhomes Grand Park"}
HTML = """<html><body><main><h1>Căn hộ Vinhomes Grand Park</h1>
<div>1 PN • Chung cư 2,1 tỷ 70 triệu/m² 30 m²</div>
<div>Dự Án: Vinhomes Grand Park Nhấn để xem thông tin về dự án</div>
<div>Cập nhật 10 giờ trước</div><div>Thông tin dự án Vinhomes Grand Park 44 - 59 triệu/m²</div>
</main></body></html>"""


class StableListingTests(unittest.TestCase):
    def test_project_listing_parses_without_inferred_period(self):
        row, status = m.parse_listing(HTML, URL, PROJECTS)
        self.assertEqual(status, "parsed-listing")
        self.assertEqual(row["project_id"], "vinhomes-grand-park")
        self.assertEqual(row["listing_price_vnd"], 2100000000)
        self.assertEqual(row["publisher_unit_asking_vnd_per_m2"], 70000000)
        self.assertIsNone(row["source_price_period"])
        self.assertEqual(row["verification_status"], "unreviewed-candidate")

    def test_project_mismatch_rejected(self):
        self.assertEqual(m.parse_listing(HTML.replace("Dự Án: Vinhomes Grand Park", "Dự Án: Akari City"), URL, PROJECTS)[1], "not-an-allowlisted-project")

    def test_price_inconsistency_rejected(self):
        self.assertEqual(m.parse_listing(HTML.replace("70 triệu", "95 triệu"), URL, PROJECTS)[1], "inconsistent-price-area-units")

    def test_rent_and_offdomain_rejected(self):
        self.assertEqual(m.parse_listing(HTML.replace("Căn hộ Vinhomes Grand Park</h1>", "Cho thuê căn hộ Vinhomes Grand Park</h1>"), URL, PROJECTS)[1], "rental-not-sale")
        self.assertEqual(m.parse_listing(HTML, URL.replace("www.nhatot.com", "untrusted.invalid"), PROJECTS)[1], "untrusted-url")

    def test_auto_discover_links_and_dedup(self):
        page = '<a href="/mua-ban-can-ho-chung-cu-thanh-pho-thu-duc-tp-ho-chi-minh/135013161.htm">A</a>' * 3
        self.assertEqual(m.discover(page, INDEX), [URL])

    def test_candidates_preserve_source_and_dont_relabel_on_next_run(self):
        cfg = {"categories": [{"id": "a", "url": INDEX}], "projects": PROJECTS}
        def fake_fetch(session, url):
            if url == INDEX:
                return f'<a href="{URL}">listing</a>', "reachable"
            if url == URL:
                return HTML, "reachable"
            raise AssertionError(url)
        with patch.object(m, "fetch_html", side_effect=fake_fetch):
            once, report = m.collect(cfg, {"data": []}, None, "2026-10-09T07:00:00Z")
            twice, rereport = m.collect(cfg, once, None, "2026-10-09T10:00:00Z")
        self.assertEqual(report["new_listing_candidates"], 1)
        self.assertEqual(rereport["new_listing_candidates"], 0)
        self.assertEqual(twice["record_count"], 1)
        self.assertEqual(twice["data"][0]["captured_at"], "2026-10-09T07:00:00Z")
        self.assertFalse(rereport["production_changed"])


if __name__ == "__main__":
    unittest.main()
