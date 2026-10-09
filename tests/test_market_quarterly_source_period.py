"""Phase 4H stable quarterly source: strict attribution from living official report."""
import unittest
from scripts.market_quarterly_source_period import source_quarter

APARTMENT = ("APARTMENT FOR SALE NEW SUPPLY: ACKNOWLEDGING SUPPLY CONTRACTION "
             "New supply officially launched in Q2 2026 continued to face contraction, "
             "reaching over 1,300 units (+7% QoQ; -53% YoY). "
             "The Q1 2026 comparison is for reference only.")
LANDED = ("LANDED PROPERTY SUPPLY: NEW SUPPLY DYNAMICS "
          "In Q2 2026, the primary market witnessed a substantial influx "
          "of new inventory, with approximately 1,700 units. ")


class QuarterlySourcePeriodTests(unittest.TestCase):
    def test_real_source_pattern_recovers_2026q2(self):
        x = source_quarter("<html><body>" + APARTMENT + LANDED + "</body></html>")
        self.assertEqual(x["period"], "2026-Q2")
        self.assertEqual(x["status"], "two-segment-agreement")

    def test_rollover_to_new_quarter_without_code_change(self):
        page = (APARTMENT + LANDED).replace("Q2 2026", "Q3 2026")
        self.assertEqual(source_quarter(page)["period"], "2026-Q3")

    def test_ignore_comparison_quarter(self):
        page = APARTMENT + LANDED + "Comparing Q1 2026 and Q4 2025."
        self.assertEqual(source_quarter(page)["period"], "2026-Q2")

    def test_reject_conflicting_segments(self):
        page = APARTMENT + LANDED.replace("Q2 2026", "Q3 2026")
        self.assertEqual(source_quarter(page)["status"], "apartment-landed-period-conflict")
        self.assertIsNone(source_quarter(page)["period"])

    def test_reject_landed_absent_or_ambiguous(self):
        self.assertIsNone(source_quarter(APARTMENT)["period"])
        doubled = APARTMENT + APARTMENT.replace("Q2 2026", "Q3 2026") + LANDED
        self.assertIsNone(source_quarter(doubled)["period"])

    def test_reject_page_with_only_generic_dates(self):
        text = "Published August 1, 2026. Q2 2026. Quarterly property market analysis."
        self.assertIsNone(source_quarter(text)["period"])


if __name__ == "__main__":
    unittest.main()
