"""Phase 4K.1 — source observation lag is not a workflow or publish date."""
import unittest
from datetime import datetime, date, timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_data_health import (business_days_elapsed, source_observation, trusted_run_url,
                               workflow_info, prod_info, load)
ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,10,9,13,0,tzinfo=timezone.utc)

class Freshness(unittest.TestCase):
    def test_workday_lag_and_weekends(self):
        self.assertEqual(business_days_elapsed(date(2026,10,7),date(2026,10,9)),2)
        self.assertEqual(business_days_elapsed(date(2026,10,9),date(2026,10,12)),1)
        self.assertEqual(business_days_elapsed(date(2026,10,9),date(2026,10,11)),0)
        self.assertEqual(business_days_elapsed(date(2026,10,12),date(2026,10,10)),0)

    def test_live_repository_is_late_without_claiming_fake_values(self):
        m={x["id"]:x for x in load(ROOT/"config/update_matrix.json")["datasets"]}
        daily=prod_info({"id":"macro-daily-markets"},m,NOW)
        self.assertEqual(daily["latest_source_period"],"2026-10-07")
        self.assertEqual(daily["source_business_day_lag"],2)
        self.assertEqual(daily["source_freshness"],"late")
        self.assertEqual(daily["record_count"],6)
        monthly=prod_info({"id":"macro-monthly-statistics"},m,NOW)
        self.assertEqual(monthly["latest_source_period"],"2026-09")
        self.assertEqual(monthly["source_freshness"],"release-based")
        self.assertIsNone(monthly["source_business_day_lag"])
        self.assertEqual(monthly["record_count"],5)
        self.assertEqual(prod_info({"id":"macro-policy-rates"},m,NOW)["record_count"],3)

    def test_bad_urls_and_pr_failures_never_shown_as_main_incident(self):
        legit="https://github.com/SanS-91/real-estate/actions/runs/12345"
        self.assertEqual(trusted_run_url({"html_url":legit}),legit)
        for url in ("javascript:alert(1)","https://evil.com/actions/runs/1",
                    "https://github.com/SanS-91/real-estate/actions/runs/1?x=a"):
            self.assertIsNone(trusted_run_url({"html_url":url}))
        runs=[
            {"name":"Macro Candidate Collector","head_branch":"pr-test",
             "status":"completed","conclusion":"failure","created_at":"2026-10-09T13:00:00Z"},
            {"name":"Macro Candidate Collector","head_branch":"main",
             "status":"completed","conclusion":"failure","created_at":"2026-10-09T11:00:00Z",
             "html_url":legit},
            {"name":"Macro Candidate Collector","head_branch":"main",
             "status":"completed","conclusion":"success","created_at":"2026-10-07T11:00:00Z",
             "html_url":"https://github.com/SanS-91/real-estate/actions/runs/100"}
        ]
        r=workflow_info("Macro Candidate Collector",runs)
        self.assertEqual(r["workflow_status"],"degraded")
        self.assertEqual(r["last_workflow_conclusion"],"failure")
        self.assertEqual(r["last_workflow_run_url"],legit)
        self.assertEqual(len(r["recent_attempts"]),2)
        self.assertEqual(r["last_successful_run_at"],"2026-10-07T11:00:00Z")

    def test_missing_run_is_unknown_not_success(self):
        r=workflow_info("Macro Candidate Collector",[])
        self.assertEqual(r["workflow_status"],"unknown")
        self.assertIsNone(r["last_workflow_run_url"])

    def test_missing_source_period_not_fake_zero(self):
        r=source_observation({"id":"macro-daily-markets"},[],NOW)
        self.assertEqual(r["source_freshness"],"unknown")
        self.assertIsNone(r["source_business_day_lag"])

if __name__=="__main__":
    unittest.main()
