from __future__ import annotations
import hashlib
import unittest
from datetime import datetime, timezone
from market_verified_metric_promotion import assess, prepare

URL = "https://www.cbrevietnam.com/insights/figures/ho-chi-minh-city-figures-q3-2026"
PERIOD = "2026-Q3"
TARGET_ID = "cbre-discovered-" + hashlib.sha256(URL.encode()).hexdigest()[:16]


def sample():
    return {
        "id": "obs-hcmc-apartment-2026-q3-cbre",
        "scope_type": "region-segment",
        "region_ids": ["hcmc"],
        "segment_ids": ["apartment"],
        "period": PERIOD,
        "period_type": "quarter",
        "source_id": "cbre-vietnam-market",
        "source_url": URL,
        "source_date": "2026-10-01",
        "new_supply": 850,
        "sales_units": None, "absorption_rate": None, "average_asp": None,
        "methodology_note": "CBRE report condominium supply: only 850 units Parsed automatically into candidate.",
        "source_verification": {
            "period": PERIOD,
            "publication_date_verified": True,
            "source_page": URL,
            "discovery_url": "https://www.cbrevietnam.com/insights",
            "metric_evidence": "CBRE report condominium supply: only 850 units",
        },
    }


def report():
    return {"targets":[{
        "target_id": TARGET_ID, "status": "parsed",
        "verified_source_period": PERIOD, "verified_source_date": "2026-10-01",
        "source_period_evidence_url": URL,
    }]}


class VerifiedMetricTests(unittest.TestCase):
    def setUp(self):
        self.today = datetime(2026, 10, 8, tzinfo=timezone.utc)
        self.sources = {"cbre-vietnam-market"}
        self.by_target = {TARGET_ID: report()["targets"][0]}

    def test_verifies_source_metric(self):
        self.assertIsNone(assess(sample(), self.by_target, self.today, self.sources))

    def test_rejects_number_missing_from_verbatim_evidence(self):
        row = sample()
        row["new_supply"] = 999
        self.assertEqual(assess(row, self.by_target, self.today, self.sources), "number-not-present-in-public-source-excerpt")

    def test_rejects_inconsistent_quarter(self):
        row = sample()
        row["period"] = "2026-Q2"
        self.assertEqual(assess(row, self.by_target, self.today, self.sources), "record-report-period-mismatch")

    def test_prevents_unaudited_metric(self):
        row = sample()
        row["average_asp"] = 150000000
        self.assertEqual(assess(row, self.by_target, self.today, self.sources), "other-metrics-not-approved")

    def test_append_only_duplicate(self):
        row = sample()
        result, decisions = prepare(
            [{"scope_type":row["scope_type"],"region_ids":row["region_ids"],"segment_ids":row["segment_ids"],
              "period":row["period"],"source_id":row["source_id"],"new_supply":850}],
            [row], report(), self.today, self.sources,
        )
        self.assertEqual(result, [])
        self.assertEqual(decisions[0]["decision"], "unchanged")

    def test_new_quarter(self):
        result, decisions = prepare([], [sample()], report(), self.today, self.sources)
        self.assertEqual(len(result), 1)
        self.assertEqual(decisions[0]["decision"], "new")


if __name__ == "__main__":
    unittest.main()
