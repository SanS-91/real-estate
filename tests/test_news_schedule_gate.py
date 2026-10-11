import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from news_schedule_gate import BACKUP, expected_slot, parse_time, should_run

UTC = timezone.utc


class NewsGateTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 11, 0, 51, tzinfo=UTC)
        self.slot = datetime(2026, 10, 11, 0, 20, tzinfo=UTC)

    def test_slot(self):
        self.assertEqual(expected_slot(self.now), self.slot)
        self.assertEqual(expected_slot(datetime(2026, 10, 11, 0, 5, tzinfo=UTC)),
                         datetime(2026, 10, 10, 14, 20, tzinfo=UTC))

    def test_primary_always_runs(self):
        self.assertTrue(should_run("schedule", "20 0,2,4,6,8,10,12,14 * * *", self.now, self.now))

    def test_backup_skip(self):
        self.assertFalse(should_run("schedule", BACKUP, self.slot, self.now))
        self.assertTrue(should_run("schedule", BACKUP, self.slot - timedelta(seconds=1), self.now))
        self.assertTrue(should_run("schedule", BACKUP, None, self.now))

    def test_manual_always_runs(self):
        self.assertTrue(should_run("workflow_dispatch", "", self.now, self.now))

    def test_untrusted_naive_time(self):
        self.assertIsNone(parse_time("2026-10-11T00:20:00"))


if __name__ == "__main__":
    unittest.main()
