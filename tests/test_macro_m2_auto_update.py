from __future__ import annotations
import json
import shutil
import sys
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from collectors.nso_banking_activity import parse_nso_banking_activity
from candidate_pipeline import build_publish_readiness
from persist_monthly_macro import build_monthly_persistence


def dump(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parser_tests():
    html = """<html><head><meta property="article:published_time" content="2026-01-06T09:00:00+07:00"></head>
    <body><p>Tính đến thời điểm 22/12/2025, tổng phương tiện thanh toán tăng 14,98% so với cuối năm 2024
    (cùng thời điểm năm trước tăng 9,15%); huy động vốn của các tổ chức tín dụng tăng 13,68%
    (cùng thời điểm năm trước tăng 8,79%); tăng trưởng tín dụng của nền kinh tế đạt 17,65%
    (cùng thời điểm năm trước tăng 13,4%).</p></body></html>"""
    parsed = parse_nso_banking_activity(html, "https://www.nso.gov.vn/bai-top/2026/01/example/", "2026-01-06T04:00:00Z")
    d = {x["indicator_id"]: x for x in parsed}
    assert len(d) == 3, d
    m2 = d["m2-growth-ytd"]
    assert (m2["value"], m2["period"], m2["data_date"], m2["as_of_date"]) == (14.98, "2025-12", "2025-12-22", "2025-12-22")
    assert m2["comparison_base"] == "previous-year-end"
    for row in parsed:
        row["id"] = "fixture-" + row["indicator_id"]
    ready = {r["indicator_id"]: r["status"] for r in build_publish_readiness(parsed, "2026-01-06T04:00:00Z")["data"]}
    assert ready["m2-growth-ytd"] == "ready-canonical", ready

    # Reject absence of explicit previous-year-end base; never relabel YoY as YTD.
    policy=json.loads((ROOT / "config/monthly_auto_persistence_policy.json").read_text(encoding="utf-8"))
    assert policy["max_period_lag_months"] == 2
    assert policy["max_m2_period_lag_months"] == 8
    workflow=(ROOT / ".github/workflows/macro-candidate.yml").read_text(encoding="utf-8")
    assert workflow.count('55 3 * * 1') == 4
    assert "github.event.schedule == '55 3 * * 1'" in workflow

    for altered in [
        html.replace("so với cuối năm 2024", "so với cùng kỳ năm 2024"),
        html.replace("so với cuối năm 2024", "so với cuối năm 2023"),
        html.replace("22/12/2025", "22/11/2025"),
    ]:
        values = parse_nso_banking_activity(altered, "https://www.nso.gov.vn/example/", "2026-01-06T04:00:00Z")
        assert not any(r["indicator_id"] == "m2-growth-ytd" for r in values), values

    # Current September 2026 NSO release contains credit/funding but may omit M2.
    # In that case the pipeline must keep existing data rather than hallucinate M2.
    existing = (ROOT / "tests/fixtures/nso_banking_activity_sample.html").read_text(encoding="utf-8")
    old_rows = parse_nso_banking_activity(existing, "https://www.nso.gov.vn/example/", "2026-10-05T02:00:00Z")
    assert {r["indicator_id"] for r in old_rows} == {"bank-funding-growth-ytd", "credit-growth-ytd"}


def persist_tests():
    # Synthetic fixture: no real 2026 September M2 value is being asserted.
    current = json.loads((ROOT / "data/processed/macro/observations.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "data/processed/macro/repository-publish.json").read_text(encoding="utf-8"))
    assert "m2-growth-ytd" not in {r["indicator_id"] for r in current["data"]}
    template = deepcopy(next(r for r in current["data"] if r["indicator_id"] == "credit-growth-ytd"))
    template.update({
        "id": "synthetic-test-only-m2-2026-09",
        "source_record_id": "synthetic-test-only-m2-2026-09",
        "indicator_id": "m2-growth-ytd",
        "period": "2026-09",
        "period_type": "month",
        "data_date": "2026-09-25",
        "as_of_date": "2026-09-25",
        "value": 7.51,
        "comparison_base": "previous-year-end",
        "reporting_cadence": "quarterly",
        "source_url": "https://www.nso.gov.vn/bai-top/2026/10/synthetic-test-only/",
        "methodology_note": "Synthetic test of prior-December reporting basis; never deployed to production.",
    })
    incoming = deepcopy(current)
    incoming["repository_publish"] = False
    incoming["frontend_publish"] = False
    incoming["source_run_id"] = "m2-regression-test"
    incoming["data"].append(template)
    incoming["record_count"] = len(incoming["data"])
    run = {"mode": "controlled-production-v1", "conflict_count": 0,
           "final_record_count": len(incoming["data"]),
           "prior_record_count": len(current["data"]),
           "source_run_id": "m2-regression-test"}

    work = Path(tempfile.mkdtemp(prefix="m2safe-"))
    try:
        repo, inc, report = (work / key for key in ("repo", "incoming", "report"))
        dump(repo / "observations.json", current)
        dump(repo / "repository-publish.json", metadata)
        dump(inc / "observations.json", incoming)
        dump(inc / "promotion-run.json", run)

        def attempt(n=0):
            return build_monthly_persistence(
                inc, repo, report,
                source_run_number=int(metadata.get("source_run_number") or 500) + 1000 + n,
                source_run_database_id="m2-test-" + str(n),
                auto_policy_path=ROOT / "config/monthly_auto_persistence_policy.json",
                monthly_gate_path=ROOT / "config/monthly_macro_production_gate.json",
                as_of=datetime(2026, 11, 5, 10, 45, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
            )
        result = attempt()
        assert result["status"] == "ready-to-commit", result
        assert result["added_record_count"] == 1
        assert (repo / "observations.json").exists()
        # Each malformed definition is rejected before repository changes.
        for idx, bad in enumerate([
            {"comparison_base": "year-on-year"},
            {"as_of_date": "2026-08-25"},
            {"reporting_cadence": "monthly"},
            {"period": "2026-08", "data_date": "2026-08-25", "as_of_date": "2026-08-25"},
        ], start=1):
            dump(repo / "observations.json", current)
            changed = deepcopy(incoming)
            changed["data"][-1].update(bad)
            dump(inc / "observations.json", changed)
            try:
                attempt(idx)
            except ValueError as exc:
                assert "M2 YTD" in str(exc), str(exc)
            else:
                raise AssertionError("Invalid M2 metadata passed monthly safety gate")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    parser_tests()
    persist_tests()
    print("PASS M2 NSO parser, canonical readiness, optional release, strict YTD gate and negative fixtures")
