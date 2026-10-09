"""Regression tests for Phase 4H evidence counters and source-type isolation."""
import unittest
from scripts.market_source_reliability import update


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.targets = {"targets": [
            {"target_id": "monthly", "source_id": "onehousing-vn", "project_id": "p", "mode": "monthly-price-candidate", "metric_type": "price"},
            {"target_id": "historical", "source_id": "rever-vn", "project_id": "p", "mode": "historical-reference-monitor", "metric_type": "launch"},
        ]}

    def report(self, status):
        return {"checks": [
            {"target_id": "monthly", "status": status, "http_status": 200},
            {"target_id": "historical", "status": "reachable-historical-reference-frozen", "http_status": 200},
        ]}

    def test_reject_reachable_html_as_verified_price(self):
        result = update({}, self.targets, self.report("reachable-no-verifiable-metric"), "1", "now")
        self.assertEqual(result["targets"][0]["classification"], "needs-stable-alternative")
        self.assertEqual(result["targets"][0]["parseable_check_count"], 0)
        self.assertEqual(result["targets"][1]["classification"], "historical-only")

    def test_repeatable_only_after_two_independent_runs(self):
        a = update({}, self.targets, self.report("same-period-unchanged"), "1", "now")
        self.assertEqual(a["targets"][0]["classification"], "source-parseable-not-yet-repeatable")
        b = update(a, self.targets, self.report("same-period-unchanged"), "2", "later")
        self.assertEqual(b["targets"][0]["classification"], "repeatably-parseable")
        c = update(b, self.targets, self.report("same-period-unchanged"), "2", "later")
        self.assertEqual(c["targets"][0]["check_count"], 2)

    def test_recent_source_failure_demotes_reliability(self):
        a = update({}, self.targets, self.report("same-period-unchanged"), "1", "now")
        b = update(a, self.targets, self.report("same-period-unchanged"), "2", "later")
        c = update(b, self.targets, self.report("reachable-no-verifiable-metric"), "3", "later")
        self.assertEqual(c["targets"][0]["classification"], "needs-stable-alternative")


if __name__ == "__main__":
    unittest.main()
