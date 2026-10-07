from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "scripts/build_update_status.py"

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "status.json"
    subprocess.run([
        sys.executable, str(script),
        "--as-of", "2026-10-07T14:34:00+07:00",
        "--output", str(out),
    ], cwd=ROOT, check=True, capture_output=True, text=True)
    status = json.loads(out.read_text(encoding="utf-8"))

assert status["dataset_count"] == 10
assert status["overall_status"] == "healthy"
by_id = {x["id"]: x for x in status["datasets"]}

production = json.loads((ROOT / "data/processed/macro/observations.json").read_text(encoding="utf-8"))
daily_ids = {"usd-vnd-central-rate", "sjc-gold-buy", "sjc-gold-sell"}
daily_rows = [row for row in production["data"] if row.get("indicator_id") in daily_ids]
assert by_id["macro-daily-markets"]["record_count"] == len(daily_rows)
assert by_id["macro-daily-markets"]["latest_observation_period"] == max(row["period"] for row in daily_rows)
assert by_id["macro-monthly-statistics"]["record_count"] == 5
assert by_id["macro-customer-rates"]["record_count"] == 4
assert by_id["macro-policy-rates"]["record_count"] == 3
assert by_id["macro-policy-rates"]["latest_observation_period"] == "2023-06-19"
assert by_id["legal-registry"]["record_count"] == 9
assert by_id["infrastructure-registry"]["record_count"] == 8
assert by_id["market-project-registry"]["record_count"] == 8
assert by_id["market-benchmarks"]["record_count"] == 7
assert by_id["home-derived"]["freshness"] == "derived"
assert by_id["search-index"]["freshness"] == "derived"
assert all(x["failure_behavior"] == "retain-last-good" for x in status["datasets"])

repo_status = json.loads((ROOT / "data/state/update-status.json").read_text(encoding="utf-8"))
assert repo_status["dataset_count"] == 10
assert repo_status["overall_status"] == "healthy"

print("Phase 4.4B update status tests PASS")
