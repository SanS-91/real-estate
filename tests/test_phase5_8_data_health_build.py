from pathlib import Path
import json, subprocess, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]
out=Path(tempfile.mkdtemp())/"data-health.json"
cp=subprocess.run([
    sys.executable,str(ROOT/"scripts/build_data_health.py"),
    "--workflow-runs-fixture",str(ROOT/"tests/fixtures/workflow_runs_health_sample.json"),
    "--as-of","2026-10-08T08:00:00+00:00",
    "--output",str(out)
],cwd=ROOT,capture_output=True,text=True)
assert cp.returncode==0,cp.stdout+"\n"+cp.stderr
payload=json.loads(out.read_text(encoding="utf-8"))
mods={x["module"]:x for x in payload["modules"]}
rows={x["id"]:x for x in payload["datasets"]}

assert set(mods)=={"market","legal","infrastructure","macro"}
assert rows["infrastructure-registry"]["workflow_status"]=="degraded"
assert mods["infrastructure"]["status"]=="degraded"
assert rows["legal-registry"]["workflow_status"]=="healthy"
assert rows["market-listing"]["source_access"]=="assisted-browser"
assert rows["market-benchmarks"]["candidate_backlog"]==0
assert payload["overall_status"] in {"degraded","stale"}
assert payload["schema_version"]==1

print("Phase 5.8 data health build integration PASS")
