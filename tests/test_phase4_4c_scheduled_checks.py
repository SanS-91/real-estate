from pathlib import Path
import json, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / ".github/workflows/data-freshness-check.yml").read_text(encoding="utf-8")
builder = ROOT / "scripts/build_update_status.py"
summary = ROOT / "scripts/write_update_status_summary.py"

assert "name: Data Freshness Check" in workflow
assert "cron: '45 0 * * *'" in workflow
assert "permissions:\n  contents: read" in workflow
assert "build_update_status.py" in workflow
assert "write_update_status_summary.py" in workflow
assert "upload-artifact@v4" in workflow

for forbidden in [
    "git push", "git commit", "contents: write", "candidate_pipeline.py",
    "promote_production.py", "macro-production-persist", "curl ", "wget "
]:
    assert forbidden not in workflow, forbidden

with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "status.json"
    subprocess.run(
        [sys.executable, str(builder), "--output", str(out),
         "--as-of", "2026-10-07T14:34:00+07:00"],
        cwd=ROOT, check=True, capture_output=True, text=True
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["dataset_count"] == 10
    assert payload["overall_status"] == "healthy"

    rendered = subprocess.run(
        [sys.executable, str(summary), "--input", str(out)],
        cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    assert "# Data Freshness Check" in rendered
    assert "FX & Gold" in rendered
    assert "Official Legal Registry" in rendered
    assert "Read-only check" in rendered

print("Phase 4.4C lightweight scheduled check tests PASS")
