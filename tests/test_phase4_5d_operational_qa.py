"""Macro operational QA regression: allow append-only growth, never bypass safety checks."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = json.loads((ROOT / "data/processed/macro/observations.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="p45d-") as folder:
        output = Path(folder) / "qa.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/phase45_operational_qa.py"), "--output", str(output)],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
        report = json.loads(output.read_text(encoding="utf-8"))

    # Check the current repository baseline, not the old fixed count of 18.
    # The QA script itself independently verifies uniqueness, complete indicator
    # coverage, immutable logical keys and safe repository-only policy flags.
    assert report["status"] == "pass", report.get("errors")
    assert not report["errors"]
    assert report["record_count"] == source["record_count"] == len(source["data"])
    coverage = report["groups"]
    required = {
        "daily-fx-gold": 3,
        "monthly-official": 5,
        "customer-rates": 4,
        "policy-rates": 3,
    }
    for group, minimum in required.items():
        assert len(coverage[group]) == minimum, (group, coverage[group])

    workflow = (ROOT / ".github/workflows/data-freshness-check.yml").read_text(encoding="utf-8")
    assert "phase45_operational_qa.py" in workflow
    print(f"Phase 4.5D operational QA PASS: {report['record_count']} verified records")


if __name__ == "__main__":
    main()
