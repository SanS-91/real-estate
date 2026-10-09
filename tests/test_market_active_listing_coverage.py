"""Phase 4I.7: compare actual recent unit-level evidence to monitored projects."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from market_active_listing_coverage import build, is_current_offer

NOW=datetime(2026,10,9,13,0,tzinfo=timezone.utc)
PROJECTS={"data":[
    {"id":"mizuki-park","name":"Mizuki Park"},
    {"id":"eaton-park","name":"Eaton Park"},
    {"id":"izumi-city","name":"Izumi City"},
]}
M={"targets":[{"project_id":"mizuki-park"},{"project_id":"eaton-park"}]}
R={"targets":[{"project_id":"eaton-park"}]}
MUABAN_HEALTH={
    "generated_at":"2026-10-09T12:00:00+00:00",
    "sources":[
        {"project_id":"mizuki-park","access":"reachable","qualified":3,"discovered":7},
        {"project_id":"eaton-park","access":"reachable","qualified":0,"discovered":1}
    ],
}
REVER_HEALTH={
    "generated_at":"2026-10-09T10:00:00+00:00",
    "projects":[{"project_id":"eaton-park","recent_90_days":1,"catalogs":[{"access_status":"reachable","links_discovered":12}]}],
}
BASE={
    "source_id":"muaban-vn","project_id":"mizuki-park","listing_id":"71273471",
    "review_status":"automated-two-hosted-checks","asset_type":"apartment",
    "metric_type":"single-listing-asking-price-per-sqm",
    "source_listed_date":"2026-10-07","source_expiration_date":"2026-10-21",
    "verification_run_ids":["a","b"],"listing_price_vnd":3500000000
}


class CoverageTests(unittest.TestCase):
    def test_monitoring_is_distinct_from_published_unit_evidence(self):
        out=build(PROJECTS,M,R,MUABAN_HEALTH,REVER_HEALTH,
                  {"data":[]},{"data":[]},NOW)
        self.assertEqual(out["project_registry_count"],3)
        self.assertEqual(out["projects_monitored"],2)
        self.assertEqual(out["projects_with_current_verified_unit_offers"],0)
        self.assertEqual(out["projects_with_recent_unpublished_source_candidates"],2)
        self.assertEqual(out["current_verified_unit_ads"],0)
        row={x["project_id"]:x for x in out["projects"]}
        self.assertEqual(row["izumi-city"]["status"],"no-verified-unit-source-target")
        self.assertEqual(row["mizuki-park"]["status"],"source-qualified-awaiting-verification")
        self.assertEqual(row["mizuki-park"]["recent_eligible_ads"],3)

    def test_two_hosted_checks_and_expiry_gate(self):
        self.assertTrue(is_current_offer(BASE,NOW))
        self.assertFalse(is_current_offer({**BASE,"verification_run_ids":["a","a"]},NOW))
        self.assertFalse(is_current_offer({**BASE,"source_expiration_date":"2026-10-01"},NOW))
        self.assertFalse(is_current_offer({**BASE,"source_listed_date":"2026-06-01"},NOW))
        self.assertFalse(is_current_offer({**BASE,"review_status":"pending"},NOW))
        self.assertFalse(is_current_offer({**BASE,"project_id":"eaton-park","source_id":"unknown"},NOW))
        result=build(PROJECTS,M,R,MUABAN_HEALTH,REVER_HEALTH,
                     {"data":[BASE]},{"data":[]},NOW)
        self.assertEqual(result["current_verified_unit_ads"],1)
        self.assertEqual(result["projects_with_current_verified_unit_offers"],1)
        self.assertNotIn("average_asp",str(result))
        self.assertNotIn("listing_price_vnd",str(result))

    def test_rever_older_than_90_days_excluded(self):
        row={
            **BASE, "source_id":"rever-vn","project_id":"eaton-park",
            "source_updated_date":"2026-07-01"
        }
        self.assertFalse(is_current_offer(row,NOW))
        self.assertTrue(is_current_offer(
            {**row,"source_updated_date":"2026-08-01"},NOW))
        report=build(PROJECTS,M,R,MUABAN_HEALTH,REVER_HEALTH,{"data":[]},
                     {"data":[row]},NOW)
        self.assertEqual(report["current_verified_unit_ads"],0)

    def test_stale_source_report_does_not_pretend_recent_candidates(self):
        old={**MUABAN_HEALTH,"generated_at":"2026-09-01T12:00:00+00:00"}
        report=build(PROJECTS,M,R,old,REVER_HEALTH,{"data":[]},{"data":[]},NOW)
        mizuki=next(r for r in report["projects"] if r["project_id"]=="mizuki-park")
        self.assertEqual(mizuki["recent_eligible_ads"],0)
        self.assertEqual(mizuki["sources"][0]["access_status"],"not-measured-recently")
        self.assertIsNone(mizuki["sources"][0]["recent_eligible_ads"])

    def test_duplicate_source_id_deduplicated(self):
        report=build(PROJECTS,M,R,MUABAN_HEALTH,REVER_HEALTH,
                     {"data":[BASE,BASE]},{"data":[]},NOW)
        self.assertEqual(report["current_verified_unit_ads"],1)


if __name__=="__main__":
    unittest.main()
