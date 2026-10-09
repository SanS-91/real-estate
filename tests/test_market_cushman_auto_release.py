"""Strict quarterly MarketBeat automatic release checks; no synthetic history."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import market_cushman_auto_release as a

HTML = """<html><body><h1>Ho Chi Minh City Residential MarketBeat</h1>
<h2>APARTMENT FOR SALE</h2><h3>NEW SUPPLY: ACKNOWLEDGING SUPPLY CONTRACTION</h3>
<p>New supply officially launched in Q3 2026 continued to face significant contraction,
reaching over 1,500 units (+7% QoQ; -53% YoY).</p>
<h3>DEMAND</h3><p>The market recorded an absorption rate of 35% of newly launched primary supply.</p>
<h2>LANDED PROPERTY</h2><h3>SUPPLY: NEW SUPPLY DYNAMICS</h3>
<p>In Q3 2026, the primary market witnessed a substantial influx of new inventory.</p>
</body></html>"""
NOW = datetime(2026, 10, 9, 7, 0, tzinfo=timezone.utc)
BASE = [{
    "id": "obs-hcmc-apartment-2026-q2-cushman",
    "scope_type": "region-segment", "segment_ids": ["apartment"],
    "source_id": a.SOURCE_ID, "period": "2026-Q2",
    "new_supply_lower_bound": 1300, "new_supply": None,
    "absorption_rate": .31,
}]


class QuarterlyReleaseTests(unittest.TestCase):
    def test_extract_source_period_and_exact_absorption(self):
        result, status = a.extract(HTML, NOW)
        self.assertEqual(status, "matched-source-quarter-and-metrics")
        self.assertEqual(result["period"], "2026-Q3")
        self.assertEqual(result["new_supply_lower_bound"], 1500)
        self.assertEqual(result["absorption_rate"], .35)

    def test_two_independent_hours_needed_and_idempotent(self):
        first, record, reason = a.check(BASE, {}, HTML, NOW, "run1")
        self.assertIsNone(record)
        self.assertEqual(reason, "need-two-consecutive-source-matches")
        second, record, reason = a.check(BASE, first, HTML, NOW + timedelta(minutes=45), "run2")
        self.assertIsNone(record)
        self.assertEqual(reason, "checks-under-one-hour-apart")
        third, record, reason = a.check(BASE, second, HTML, NOW + timedelta(hours=2), "run3")
        self.assertEqual(reason, "two-independent-quarterly-metrics-verified")
        self.assertEqual(record["period"], "2026-Q3")
        self.assertIsNone(record["source_date"])
        self.assertIsNone(record["new_supply"])
        self.assertEqual(record["new_supply_lower_bound"], 1500)
        self.assertEqual(record["review_status"], "automated-source-verified")
        fourth, duplicate, reason = a.check(BASE + [record], third, HTML, NOW + timedelta(hours=3), "run4")
        self.assertIsNone(duplicate)
        self.assertEqual(reason, "already-published")

    def test_conflict_in_last_check_blocks(self):
        first, _, _ = a.check(BASE, {}, HTML, NOW, "1")
        edited = HTML.replace("35% of", "45% of")
        _, record, reason = a.check(BASE, first, edited, NOW + timedelta(hours=2), "2")
        self.assertIsNone(record)
        self.assertEqual(reason, "need-two-consecutive-source-matches")

    def test_same_run_never_forges_independent_check(self):
        first, _, _ = a.check(BASE, {}, HTML, NOW, "1")
        next_state, candidate, why = a.check(BASE, first, HTML, NOW + timedelta(hours=2), "1")
        self.assertEqual(len(next_state["checks"]), 1)
        self.assertIsNone(candidate)

    def test_old_quarter_cannot_be_reissued(self):
        old_html = HTML.replace("Q3 2026", "Q2 2026").replace("1,500", "1,300").replace("35%", "31%")
        _, candidate, result = a.check(BASE, {}, old_html, NOW, "1")
        self.assertIsNone(candidate)
        self.assertEqual(result, "already-published")

    def test_large_absorption_jump_requires_review(self):
        edited = HTML.replace("35% of", "85% of")
        state, _, _ = a.check(BASE, {}, edited, NOW, "1")
        _, candidate, status = a.check(BASE, state, edited, NOW + timedelta(hours=2), "2")
        self.assertIsNone(candidate)
        self.assertEqual(status, "absorption-jump-review-required")

    def test_missing_project_scope_period_and_metrics_never_publish(self):
        for html in (HTML.replace("LANDED PROPERTY", "MISSING LAND"),
                     HTML.replace("Q3 2026", "Q2 2026", 1),
                     HTML.replace("35% of", "unknown of")):
            state, candidate, reason = a.check(BASE, {}, html, NOW, "1")
            self.assertIsNone(candidate)
            self.assertNotEqual(reason, "two-independent-quarterly-metrics-verified")


if __name__ == "__main__":
    unittest.main()
