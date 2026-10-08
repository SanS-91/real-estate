from __future__ import annotations
import unittest
from market_period_evidence import extract_period_evidence

class PeriodEvidenceTests(unittest.TestCase):
    def test_english_quarter(self):
        self.assertEqual(extract_period_evidence("<title>HCMC residential Q3 2026</title>")["period"], "2026-Q3")
    def test_vietnamese_quarter(self):
        self.assertEqual(extract_period_evidence("<h1>Báo cáo thị trường Quý 2/2026</h1>")["period"], "2026-Q2")
    def test_ambiguous(self):
        r=extract_period_evidence("<title>Q2 2026 vs Q3 2026</title>")
        self.assertEqual(r["status"], "ambiguous")
        self.assertIsNone(r["period"])
    def test_missing(self):
        self.assertIsNone(extract_period_evidence("<h1>Residential research</h1>")["period"])

if __name__ == "__main__":
    unittest.main()
