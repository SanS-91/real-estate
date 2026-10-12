import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from macro_rss_recovery_gate import eligible_slot, decide, utc

UTC = timezone.utc


class MacroRSSRecoveryTests(unittest.TestCase):
    def test_morning_slot_on_sunday(self):
        now = datetime(2026, 10, 11, 4, 25, tzinfo=UTC)
        self.assertEqual(eligible_slot(now), datetime(2026, 10, 11, 3, 15, tzinfo=UTC))
        self.assertEqual(decide(now, [])[1], "macro-missed-or-failed")

    def test_afternoon_only_business_days(self):
        monday = datetime(2026, 10, 12, 10, 27, tzinfo=UTC)
        sunday = datetime(2026, 10, 11, 10, 27, tzinfo=UTC)
        self.assertEqual(eligible_slot(monday), datetime(2026, 10, 12, 9, 15, tzinfo=UTC))
        self.assertIsNone(eligible_slot(sunday))

    def test_ignore_before_slot_window(self):
        now = datetime(2026, 10, 12, 2, 25, tzinfo=UTC)
        self.assertEqual(decide(now, []), (False, "outside-macro-recovery-window", None))

    def test_success_skips_duplicate(self):
        now = datetime(2026, 10, 12, 4, 25, tzinfo=UTC)
        runs = [{"createdAt": "2026-10-12T03:18:00Z",
                 "event": "schedule", "status": "completed", "conclusion": "success"}]
        self.assertEqual(decide(now, runs)[1], "macro-already-success")

    def test_active_skips_duplicate(self):
        now = datetime(2026, 10, 12, 4, 25, tzinfo=UTC)
        runs = [{"createdAt": "2026-10-12T03:30:00Z",
                 "event": "workflow_dispatch", "status": "in_progress"}]
        self.assertEqual(decide(now, runs)[1], "macro-queued-or-running")

    def test_failed_or_old_run_dispatches(self):
        now = datetime(2026, 10, 12, 4, 25, tzinfo=UTC)
        runs = [
            {"createdAt": "2026-10-12T03:22:00Z", "event": "schedule",
             "status": "completed", "conclusion": "failure"},
            {"createdAt": "2026-10-11T03:22:00Z", "event": "schedule",
             "status": "completed", "conclusion": "success"}
        ]
        self.assertTrue(decide(now, runs)[0])

    def test_ignore_unrelated_events(self):
        now = datetime(2026, 10, 12, 4, 25, tzinfo=UTC)
        runs = [{"createdAt": "2026-10-12T03:22:00Z", "event": "push",
                 "status": "completed", "conclusion": "success"}]
        self.assertTrue(decide(now, runs)[0])

    def test_reject_naive_times(self):
        self.assertIsNone(utc("2026-10-12T03:15:00"))


if __name__ == "__main__":
    unittest.main()
