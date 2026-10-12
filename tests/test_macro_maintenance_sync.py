"""Maintenance must refresh after each controlled Macro publication attempt."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def main():
    macro = (ROOT / ".github/workflows/macro-candidate.yml").read_text(encoding="utf-8")
    health = (ROOT / ".github/workflows/unified-data-health.yml").read_text(encoding="utf-8")
    jobs = re.split(r"(?=^  persist-(?:daily-production|monthly-production|customer-rates-production|policy-rates-production):)", macro, flags=re.MULTILINE)[1:]
    assert len(jobs) == 4, len(jobs)
    for job in jobs:
        assert "contents: write\n      actions: write" in job, "health dispatch requires Actions write"
        assert "if: always()" in job
        assert job.count("gh workflow run unified-data-health.yml --ref main") == 1
    assert "  workflow_dispatch:" in health
    assert "  contents: write" in health
    print("PASS all 4 controlled Macro jobs request an updated Maintenance snapshot")

if __name__ == "__main__":
    main()
