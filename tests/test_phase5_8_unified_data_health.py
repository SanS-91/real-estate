from pathlib import Path
import importlib.util, json
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("health",ROOT/"scripts/build_data_health.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

runs=json.loads((ROOT/"tests/fixtures/workflow_runs_health_sample.json").read_text(encoding="utf-8"))["workflow_runs"]

wf=mod.workflow_info("Infrastructure Candidate Collector",runs)
assert wf["workflow_status"]=="degraded"
assert wf["last_successful_run_at"]=="2026-10-01T03:25:00Z"

wf2=mod.workflow_info("Legal Candidate Collector",runs)
assert wf2["workflow_status"]=="healthy"

# Market candidate rows currently mirror promoted production; backlog must not be overstated.
backlog,conflicts=mod.market_obs_backlog("data/candidate/market/observations.json")
assert backlog==0
assert conflicts==0

ops=json.loads((ROOT/"config/operations_health.json").read_text(encoding="utf-8"))
ids={x["id"] for x in ops["datasets"]}
assert {"market-listing","legal-registry","infrastructure-registry","macro-daily-markets"} <= ids

matrix=json.loads((ROOT/"config/update_matrix.json").read_text(encoding="utf-8"))
m={x["id"]:x for x in matrix["datasets"]}
assert m["legal-registry"]["update_mode"]=="automated-candidate-review"
assert m["infrastructure-registry"]["update_mode"]=="automated-candidate-review"
assert m["market-listing"]["update_mode"]=="assisted-browser"

prod=mod.prod_info(next(x for x in ops["datasets"] if x["id"]=="market-listing"),m,datetime(2026,10,8,8,0,tzinfo=timezone.utc))
assert prod["record_count"]>=12
assert prod["freshness"] in {"fresh","due","stale","current"}

print("Phase 5.8 unified data health tests PASS")
