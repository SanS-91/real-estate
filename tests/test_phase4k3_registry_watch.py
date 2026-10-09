import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_registry_candidate_health import build

NOW="2026-10-09T18:00:00+00:00"
WATCH={
 "generated_at":NOW,"previous_baseline_available":True,
 "targets":[{"module":"legal","ok":True},{"module":"legal","ok":False},
            {"module":"infrastructure","ok":True}],
 "discovery_links":[{"module":"legal","new_since_previous_check":True},
                    {"module":"legal","new_since_previous_check":False}]
}
CANONICAL={"data":[{"id":"one"},{"id":"two"}]}
REPORT={"generated_at":NOW,"candidate_count":1,
        "results":[{"status":"parsed"},{"status":"fetch-error"}]}

class RegistryHealth(unittest.TestCase):
 def test_failing_sources_are_not_marked_healthy(self):
  r=build("legal",WATCH,REPORT,CANONICAL,NOW)
  self.assertEqual(r["status"],"source-degraded")
  self.assertEqual(r["source_targets_checked"],2)
  self.assertEqual(r["source_targets_reachable"],1)
  self.assertEqual(r["new_links_since_baseline"],1)
  self.assertEqual(r["candidates_awaiting_review_in_this_run"],1)
  self.assertFalse(r["production_written"])
  self.assertTrue(r["candidate_only"])
  self.assertNotIn("data",r)

 def test_first_watch_never_fabricates_new_links(self):
  watch={**WATCH,"previous_baseline_available":False}
  report={**REPORT,"results":[{"status":"parsed"}],"candidate_count":0}
  r=build("legal",watch,report,CANONICAL,NOW)
  self.assertEqual(r["status"],"source-degraded")
  self.assertIsNone(r["new_links_since_baseline"])
  watch["targets"]=[{"module":"legal","ok":True}]
  self.assertEqual(build("legal",watch,report,CANONICAL,NOW)["status"],"baseline-initialized")

 def test_new_items_require_review_and_missing_report_is_incomplete(self):
  report={**REPORT,"results":[{"status":"parsed"}]}
  watch={**WATCH,"targets":[{"module":"legal","ok":True}]}
  self.assertEqual(build("legal",watch,report,CANONICAL,NOW)["status"],"candidates-await-review")
  result=build("legal",watch,None,CANONICAL,NOW)
  self.assertEqual(result["status"],"incomplete")
  self.assertIsNone(result["candidates_awaiting_review_in_this_run"])

 def test_module_isolation_and_approved_production_unchanged(self):
  r=build("infrastructure",WATCH,{"candidate_count":0,"results":[]},CANONICAL,NOW)
  self.assertEqual(r["source_targets_checked"],1)
  self.assertEqual(r["new_links_since_baseline"],0)
  self.assertEqual(r["canonical_record_count"],2)
  self.assertFalse(r["production_written"])

 def test_cache_and_ui_contract(self):
  root=Path(__file__).resolve().parents[1]
  watcher=(root/"scripts/watch_registries.py").read_text()
  self.assertIn("has_previous_baseline and",watcher)
  for m in ("legal","infrastructure"):
   w=(root/f".github/workflows/{m}-candidate-collector.yml").read_text()
   self.assertIn("data/state/registry-watch-cache.json",w)
   self.assertIn(f"--module {m}",w)
   self.assertIn(f"git add data/state/{m}-candidate-health.json",w)
  js=(root/"assets/js/maintenance.js").read_text()
  html=(root/"maintenance.html").read_text()
  self.assertIn("renderOfficialRegistryWatch",js)
  self.assertIn("data-official-registry-watch",html)
  self.assertIn("candidate_only !== true",js)
if __name__=="__main__":
 unittest.main()
