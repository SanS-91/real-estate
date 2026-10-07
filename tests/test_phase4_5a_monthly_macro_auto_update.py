from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from persist_monthly_macro import build_monthly_persistence

MONTHLY_IDS = {
    "cpi-yoy",
    "cpi-mom",
    "core-cpi-yoy",
    "credit-growth-ytd",
    "bank-funding-growth-ytd",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def next_month(period: str) -> str:
    dt = datetime.strptime(period, "%Y-%m")
    year, month = dt.year, dt.month
    if month == 12:
        year += 1
        month = 1
    else:
        month += 1
    return f"{year:04d}-{month:02d}"


def next_test_period_by_indicator(current: dict) -> dict[str, str]:
    latest: dict[str, str] = {}
    for row in current["data"]:
        iid = row.get("indicator_id")
        if iid in MONTHLY_IDS and row.get("period_type") == "month":
            if iid not in latest or row.get("period", "") > latest[iid]:
                latest[iid] = row["period"]
    assert set(latest) == MONTHLY_IDS, latest
    return {iid: next_month(period) for iid, period in latest.items()}


def make_incoming(current: dict) -> tuple[dict, dict, dict[str, str]]:
    periods = next_test_period_by_indicator(current)
    rows = deepcopy(current["data"])
    latest_rows = {}
    for row in current["data"]:
        iid = row.get("indicator_id")
        if iid not in MONTHLY_IDS or row.get("period_type") != "month":
            continue
        if iid not in latest_rows or row.get("period", "") > latest_rows[iid].get("period", ""):
            latest_rows[iid] = row

    values = {
        "cpi-yoy": 5.11,
        "cpi-mom": 0.31,
        "core-cpi-yoy": 4.42,
        "credit-growth-ytd": 11.20,
        "bank-funding-growth-ytd": 10.05,
    }
    for idx, iid in enumerate(sorted(MONTHLY_IDS), 1):
        row = deepcopy(latest_rows[iid])
        row["period"] = periods[iid]
        row["value"] = values[iid]
        row["source_id"] = "nso-vietnam"
        row["source_url"] = "https://www.nso.gov.vn/tin-tuc-thong-ke/phase45a-fixture/"
        row["evidence_status"] = "verified"
        row["observation_status"] = "final"
        row["id"] = f"phase45a-{idx}-{periods[iid]}"
        row["source_record_id"] = row["id"]
        row["fetched_at"] = "2026-11-05T03:50:00+00:00"
        row["promoted_at"] = "2026-11-05T03:51:00+00:00"
        row["promotion_run_id"] = "phase45a-test"
        rows.append(row)

    rows.sort(key=lambda r: (r.get("indicator_id", ""), r.get("period", ""), r.get("id", "")))
    incoming = {
        "schema_version": 1,
        "generated_at": "2026-11-05T03:51:00+00:00",
        "record_count": len(rows),
        "production_write": True,
        "repository_publish": False,
        "frontend_publish": False,
        "source_run_id": "phase45a-test",
        "data": rows,
    }
    run = {
        "schema_version": 1,
        "generated_at": "2026-11-05T03:51:00+00:00",
        "mode": "controlled-production-v1",
        "production_write": True,
        "repository_publish": False,
        "frontend_publish": False,
        "source_run_id": "phase45a-test",
        "prior_record_count": len(current["data"]),
        "added_record_count": len(MONTHLY_IDS),
        "unchanged_record_count": 0,
        "held_record_count": 0,
        "conflict_count": 0,
        "final_record_count": len(rows),
    }
    return incoming, run, periods


def month_after_latest(periods: dict[str, str]) -> datetime:
    latest = max(periods.values())
    dt = datetime.strptime(next_month(latest), "%Y-%m")
    return datetime(dt.year, dt.month, 5, 10, 45, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))


def main():
    gate = load(ROOT / "config/monthly_macro_production_gate.json")
    policy = load(ROOT / "config/monthly_auto_persistence_policy.json")
    assert set(gate["allowed_indicators"]) == MONTHLY_IDS
    assert set(policy["allowed_indicator_ids"]) == MONTHLY_IDS
    assert policy["max_additions_per_run"] == 5
    assert policy["max_period_lag_months"] == 2
    assert policy["on_source_failure"] == "retain-last-good"
    assert set(policy["allowed_source_hosts"]) == {"nso.gov.vn", "www.nso.gov.vn"}

    wf = (ROOT / ".github/workflows/macro-candidate.yml").read_text(encoding="utf-8")
    assert "monthly-macro-production" in wf
    assert "45 3 1-10 * *" in wf
    assert "--source nso-cpi" in wf
    assert "--source nso-banking-activity" in wf
    assert "--policy config/monthly_macro_production_gate.json" in wf
    assert "persist-monthly-production:" in wf
    assert "python scripts/persist_monthly_macro.py" in wf
    assert "data(macro): auto-publish verified monthly CPI and banking growth" in wf
    assert "github.event.schedule == '15 3 * * *'" in wf
    assert "github.event.schedule == '15 9 * * 1-5'" in wf

    current = load(ROOT / "data/processed/macro/observations.json")
    current_meta = load(ROOT / "data/processed/macro/repository-publish.json")
    incoming, run, periods = make_incoming(current)
    as_of = month_after_latest(periods)

    tmp = Path(tempfile.mkdtemp(prefix="phase45a-"))
    try:
        repo = tmp / "repo"
        incoming_dir = tmp / "incoming"
        report = tmp / "report"
        dump(repo / "observations.json", current)
        dump(repo / "repository-publish.json", current_meta)
        dump(incoming_dir / "observations.json", incoming)
        dump(incoming_dir / "promotion-run.json", run)

        source_run = max(999, int(current_meta.get("source_run_number", 0)) + 1)
        result = build_monthly_persistence(
            incoming_dir,
            repo,
            report,
            source_run_number=source_run,
            source_run_database_id="phase45a-999",
            auto_policy_path=ROOT / "config/monthly_auto_persistence_policy.json",
            monthly_gate_path=ROOT / "config/monthly_macro_production_gate.json",
            as_of=as_of,
        )
        assert result["status"] == "ready-to-commit"
        assert result["added_record_count"] == 5
        assert {r["indicator_id"] for r in result["added"]} == MONTHLY_IDS
        out = load(repo / "observations.json")
        assert out["record_count"] == current["record_count"] + 5
        assert out["repository_publish"] is True
        assert out["repository_persistence_mode"] == "controlled-monthly-auto-persistence-v1"

        # Replaying the now-current production state is idempotent.
        replay = deepcopy(out)
        replay["repository_publish"] = False
        replay["frontend_publish"] = False
        for key in [
            "repository_published_at",
            "repository_source_run_number",
            "repository_source_run_database_id",
            "repository_persistence_mode",
        ]:
            replay.pop(key, None)
        replay_run = deepcopy(run)
        replay_run["prior_record_count"] = out["record_count"]
        replay_run["added_record_count"] = 0
        replay_run["final_record_count"] = out["record_count"]
        replay_run["source_run_id"] = replay["source_run_id"]
        dump(incoming_dir / "observations.json", replay)
        dump(incoming_dir / "promotion-run.json", replay_run)
        before = (repo / "observations.json").read_bytes()
        replay_result = build_monthly_persistence(
            incoming_dir,
            repo,
            report,
            source_run_number=source_run + 1,
            source_run_database_id="phase45a-1000",
            auto_policy_path=ROOT / "config/monthly_auto_persistence_policy.json",
            monthly_gate_path=ROOT / "config/monthly_macro_production_gate.json",
            as_of=as_of,
        )
        assert replay_result["status"] == "no-change"
        assert before == (repo / "observations.json").read_bytes()

        # A daily or otherwise unrelated indicator can never leak through the monthly gate.
        bad_incoming = deepcopy(incoming)
        bad_run = deepcopy(run)
        bad = deepcopy(next(r for r in current["data"] if r["indicator_id"] == "usd-vnd-central-rate"))
        bad["period"] = "2099-01-01"
        bad["id"] = "phase45a-bad-daily"
        bad["source_record_id"] = bad["id"]
        bad_incoming["data"].append(bad)
        bad_incoming["record_count"] += 1
        bad_run["final_record_count"] += 1
        bad_run["added_record_count"] += 1
        repo2 = tmp / "repo2"
        incoming2 = tmp / "incoming2"
        report2 = tmp / "report2"
        dump(repo2 / "observations.json", current)
        dump(repo2 / "repository-publish.json", current_meta)
        dump(incoming2 / "observations.json", bad_incoming)
        dump(incoming2 / "promotion-run.json", bad_run)
        try:
            build_monthly_persistence(
                incoming2,
                repo2,
                report2,
                source_run_number=source_run + 2,
                source_run_database_id="phase45a-bad",
                auto_policy_path=ROOT / "config/monthly_auto_persistence_policy.json",
                monthly_gate_path=ROOT / "config/monthly_macro_production_gate.json",
                as_of=as_of,
            )
        except ValueError as exc:
            assert "exceed max" in str(exc) or "Non-monthly indicator" in str(exc)
        else:
            raise AssertionError("Unrelated daily addition was not blocked")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("Phase 4.5A monthly Macro auto-update tests PASS")


if __name__ == "__main__":
    main()
