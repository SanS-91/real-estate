from __future__ import annotations

import unittest
from datetime import datetime, timezone
from market_source_discovery import namlong_target
from market_verified_auto_promotion import assess, prepare_updates

INDEX = "https://www.namlongvn.com/tin-tuc/"
URL = "https://www.namlongvn.com/tin-tuc/du-an-waterpoint/"


def verified_news():
    return {
        "id": "article-market-" + namlong_target(URL, INDEX)["target_id"],
        "url": URL,
        "source_id": "nam-long-official",
        "title": "Nam Long công bố cập nhật về dự án Waterpoint",
        "summary": "Bài viết chính thức về tiến độ Waterpoint và những thay đổi trong dự án.",
        "published_at": "2026-08-04T09:00:00+07:00",
        "category": "market",
        "content_type": "developer-update",
        "project_ids": ["waterpoint"],
        "source_verification": {
            "publication_date_verified": True,
            "article_page": URL,
            "discovery_url": INDEX,
        },
    }


class OfficialAutoPublishTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 8, tzinfo=timezone.utc)

    def test_accepts_verified_official_article(self):
        self.assertIsNone(assess(verified_news(), {"nam-long-official"}, {"waterpoint"}, self.now))

    def test_rejects_missing_date_proof(self):
        row = verified_news()
        row["source_verification"]["publication_date_verified"] = False
        self.assertIsNotNone(assess(row, {"nam-long-official"}, {"waterpoint"}, self.now))

    def test_rejects_future_publication(self):
        row = verified_news()
        row["published_at"] = "2027-01-01T09:00:00+07:00"
        self.assertEqual(assess(row, {"nam-long-official"}, {"waterpoint"}, self.now), "future-publication")

    def test_rejects_identity_mismatch(self):
        row = verified_news()
        row["id"] = "some-other-id"
        self.assertEqual(assess(row, {"nam-long-official"}, {"waterpoint"}, self.now), "article-identity-mismatch")

    def test_deduplicates_without_overwriting_history(self):
        row = verified_news()
        additions, decisions = prepare_updates(
            [{"url": URL, "id": "older-id"}], [row], {"nam-long-official"}, {"waterpoint"}, self.now,
        )
        self.assertEqual(additions, [])
        self.assertEqual(decisions[0]["decision"], "unchanged")

    def test_does_not_autopublish_other_source(self):
        row = verified_news()
        row["url"] = "https://some-other-developer.com/tin-tuc/du-an/"
        additions, decisions = prepare_updates([], [row], {"nam-long-official"}, {"waterpoint"}, self.now)
        self.assertEqual(additions, [])
        self.assertEqual(decisions[0]["decision"], "manual-review")


if __name__ == "__main__":
    unittest.main()
