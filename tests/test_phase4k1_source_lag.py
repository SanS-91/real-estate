"""Phase 4K.1 — source observation lag is not a workflow or publish date."""
import unittest
from datetime import datetime, date, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
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

    def test_source_lag_classification_uses_real_publisher_period(self):
        # Deterministic regression independent of future production updates.
        fixture=[{"indicator_id":"usd-vnd-central-rate","period_type":"day",
                  "period":"2026-10-07","data_date":"2026-10-07",
                  "observation_status":"final"}]
        result=source_observation({"id":"macro-daily-markets"},fixture,NOW)
        self.assertEqual(result["latest_source_period"],"2026-10-07")
        self.assertEqual(result["source_business_day_lag"],2)
        self.assertEqual(result["source_freshness"],"late")
        fixture[0]["period"]="2026-10-09"
        fixture[0]["data_date"]="2026-10-09"
        current=source_observation({"id":"macro-daily-markets"},fixture,NOW)
        self.assertEqual(current["source_business_day_lag"],0)
        self.assertEqual(current["source_freshness"],"within-window")

    def test_live_repository_periods_are_computed_not_frozen_to_october_7(self):
        # Production is intentionally append-only; a successful collector
        # must not break CI just because new genuine observations were added.
        matrix={x["id"]:x for x in load(ROOT/"config/update_matrix.json")["datasets"]}
        observations=load(ROOT/"data/processed/macro/observations.json")["data"]
        now=datetime.now(timezone.utc)
        for dataset_id in ("macro-daily-markets","macro-monthly-statistics","macro-policy-rates"):
            info=prod_info({"id":dataset_id},matrix,now)
            members={r for r in matrix[dataset_id].get("indicator_ids",[])}
            expected=[r for r in observations if r.get("indicator_id") in members]
            self.assertEqual(info["record_count"],len(expected))
            if dataset_id=="macro-daily-markets" and expected:
                periods=[r.get("data_date") or r.get("period") for r in expected
                         if r.get("period_type")=="day"
                         and r.get("observation_status")=="final"]
                last=max(periods)
                days=business_days_elapsed(date.fromisoformat(last),
                    now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date())
                self.assertEqual(info["latest_source_period"],last)
                self.assertEqual(info["source_business_day_lag"],days)
                self.assertEqual(info["source_freshness"],
                                 "late" if days>1 else "within-window")
            elif expected:
                self.assertEqual(info["source_freshness"],"release-based")
                self.assertIsNone(info["source_business_day_lag"])

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
