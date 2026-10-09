"""Phase 4H source health is a separate maintenance view, not extra pricing clutter."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SourceStatusUITests(unittest.TestCase):
    def test_status_panel_is_in_maintenance_not_pricing(self):
        status = (ROOT / "maintenance.html").read_text(encoding="utf-8")
        pricing = (ROOT / "market.html").read_text(encoding="utf-8")
        self.assertIn('data-market-source-health', status)
        self.assertNotIn('data-market-source-health', pricing)

    def test_runtime_uses_generated_source_status_not_hardcoded_metrics(self):
        script = (ROOT / "assets/js/maintenance.js").read_text(encoding="utf-8")
        self.assertIn("data/state/market-source-reliability.json", script)
        self.assertIn("data/state/market-stable-listing-health.json", script)
        self.assertIn("repeatably-parseable", script)
        self.assertIn("access-blocked", script)
        self.assertIn("esc(cell)", script)
        self.assertIn("renderMarketSourceHealth();", script)


if __name__ == "__main__":
    unittest.main()
