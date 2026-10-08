from __future__ import annotations
import unittest
from market_source_discovery import discover_namlong_links, namlong_target
from collectors.namlong_official import parse_article


class DiscoveryTests(unittest.TestCase):
    def test_official_article_only(self):
        html = """
        <a href="/tin-tuc/">Tin tức</a>
        <a href="/tin-tuc/du-an-waterpoint/">Waterpoint</a>
        <a href="https://www.namlongvn.com/tin-tuc/du-an-waterpoint/?utm=x">duplicate</a>
        <a href="https://other.com/tin-tuc/fake/">fake</a>
        <a href="/tin-tuc/du-an-izumi/">Izumi</a>
        """
        links = discover_namlong_links(html, "https://www.namlongvn.com/tin-tuc/")
        self.assertEqual(links, [
            "https://www.namlongvn.com/tin-tuc/du-an-waterpoint/",
            "https://www.namlongvn.com/tin-tuc/du-an-izumi/",
        ])

    def test_stable_id(self):
        url = "https://www.namlongvn.com/tin-tuc/du-an-waterpoint/"
        a = namlong_target(url, "https://www.namlongvn.com/tin-tuc/")
        b = namlong_target(url, "https://www.namlongvn.com/tin-tuc/")
        self.assertEqual(a["target_id"], b["target_id"])
        self.assertTrue(a["auto_discovered"])

    def test_article_excludes_navigation_related_news(self):
        html = """
        <nav>Akari City Izumi City</nav>
        <div>04/08/2026</div><h1>Tiến độ Waterpoint</h1>
        <p>Dự án Waterpoint đã bàn giao phân khu đầu tiên.</p>
        <h2>Tin tức khác</h2><p>Mizuki Park đã ra mắt.</p>
        <footer>Izumi City Mizuki Park</footer>
        """
        row = parse_article(html, "https://www.namlongvn.com/tin-tuc/test/", "2026-10-08")
        self.assertEqual(row["published_date"], "2026-08-04")
        self.assertEqual(row["project_ids"], ["waterpoint"])

    def test_missing_article_date_requires_review(self):
        row = parse_article("<h1>Waterpoint update</h1><p>Waterpoint</p>", "https://www.namlongvn.com/tin-tuc/test/", "")
        self.assertIsNone(row["published_date"])


if __name__ == "__main__":
    unittest.main()
