"""Regression suite: Savills report discovery and source-date gates."""
import unittest
from collectors.savills_research import parse_article
from market_publication_evidence import extract_publication_date
from market_source_discovery import discover_savills_reports

REPORT = "https://www.savills.com.vn/research_articles/226576/239332-0/viet-nam-real-estate-market-brief-q3-2026"
INDEX = "https://www.savills.com.vn/insight-and-opinion/research.aspx?f=date&p=&page=0&q=&rc=Vietnam&t="
HEAD = "Viet Nam Real Estate Market Brief Q3/2026"


def source(title=HEAD, date="<meta property='article:published_time' content='2026-10-15T10:00:00+07:00'>"):
    return ("<html><head><title>" + title + "</title>" + date +
        "</head><body><h1>" + title + "</h1>" +
        "<h2>HCMC OVERVIEW</h2><p>In Q3/2026, demand remained selective.</p></body></html>")


class SavillsSourceGateTests(unittest.TestCase):
    def test_source_dated_exact_quarter(self):
        r = parse_article(source(), REPORT, "2026-11-02T08:00:00Z")
        self.assertEqual(r["report_period"], "2026-Q3")
        self.assertEqual(r["published_date"], "2026-10-15")
        self.assertNotIn("sales_units", r)
        self.assertNotIn("average_asp", r)
        self.assertNotIn("1300", str(r))

    def test_day_month_publisher_date(self):
        html = source(date="").replace("</h1>", "</h1><p>15 October 2026</p>")
        self.assertEqual(extract_publication_date(html)["date"], "2026-10-15")

    def test_vietnamese_publisher_date(self):
        html = source(date="").replace("</h1>", "</h1><p>15 Tháng 10 Năm 2026</p>")
        self.assertEqual(extract_publication_date(html)["date"], "2026-10-15")

    def test_missing_date_rejected(self):
        with self.assertRaisesRegex(ValueError, "publication-date"):
            parse_article(source(date=""), REPORT, "2026-11-02T08:00:00Z")

    def test_wrong_host_and_landing_page_rejected(self):
        for url in ["https://unknown.example/research_articles/226576/239332-0",
                    "https://www.savills.com.vn/insight-and-opinion/"]:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    parse_article(source(), url, "2026-11-02T08:00:00Z")

    def test_stale_hardcoded_q2_title_rejected(self):
        with self.assertRaises(ValueError):
            parse_article(source(title="Generic real estate statistics"), REPORT, "2026-11-02T08:00:00Z")

    def test_discovery_does_not_accept_unrelated_reports(self):
        html = ("<article><h3>Viet Nam Real Estate Market Brief Q3/2026</h3>"
            "<a href='/research_articles/226576/239332-0/viet-nam-real-estate-market-brief-q3-2026'>Read Now</a></article>"
            "<article><h3>London office Q3 2026</h3>"
            "<a href='/research_articles/226576/990000-1/office-q3'>Read Now</a></article>")
        result = discover_savills_reports(html, INDEX)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["period"], "2026-Q3")
        self.assertEqual(result[0]["review_policy"], "report-candidate-only; no numeric promotion")


if __name__ == "__main__":
    unittest.main()
