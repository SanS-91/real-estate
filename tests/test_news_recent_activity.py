"""Regression for source publication recency, separate from RSS polling."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from market_news_rss import summarize_archive_activity

class RecentNewsActivityTests(unittest.TestCase):
    def test_multimodule_and_actual_publication_time(self):
        now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
        rows = [
            {"content_type": "publisher-rss", "category": "market", "module_ids": ["market", "legal"], "published_at": "2026-10-31T09:00:00+00:00"},
            {"content_type": "publisher-rss", "category": "macro", "module_ids": ["macro"], "published_at": "2026-10-20T09:00:00+00:00"},
            {"content_type": "publisher-rss", "category": "infrastructure", "published_at": "2026-09-01T09:00:00+00:00"},
            {"content_type": "publisher-rss", "category": "market", "published_at": "2026-11-10T09:00:00+00:00"},
            {"content_type": "official-update", "category": "legal", "published_at": "2026-11-01T09:00:00+00:00"},
            {"content_type": "publisher-rss", "category": "market", "published_at": "bad date"},
        ]
        report = summarize_archive_activity(rows, now)
        self.assertEqual(report["recent_by_module_7d"], {"market": 1, "legal": 1, "infrastructure": 0, "macro": 0})
        self.assertEqual(report["recent_by_module_30d"], {"market": 1, "legal": 1, "infrastructure": 0, "macro": 1})
        self.assertEqual(report["latest_published_by_module"]["market"], "2026-10-31T09:00:00+00:00")
        self.assertEqual(report["latest_published_by_module"]["infrastructure"], "2026-09-01T09:00:00+00:00")

if __name__ == "__main__":
    unittest.main()
