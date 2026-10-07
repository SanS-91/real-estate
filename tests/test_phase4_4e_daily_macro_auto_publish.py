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

from persist_daily_markets import build_daily_persistence

DAILY_IDS = {"usd-vnd-central-rate", "sjc-gold-buy", "sjc-gold-sell"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_incoming(current: dict, period: str = "2026-10-07") -> tuple[dict, dict]:
    rows = deepcopy(current["data"])
    by = {r["indicator_id"]: r for r in rows if r["indicator_id"] in DAILY_IDS}
    values = {
        "usd-vnd-central-rate": 25638.0,
        "sjc-gold-buy": 140500000.0,
        "sjc-gold-sell": 143500000.0,
    }
    for idx, iid in enumerate(sorted(DAILY_IDS), 1):
        row = deepcopy(by[iid])
        row["period"] = period
        row["data_date"] = period
        row["value"] = values[iid]
        row["id"] = f"phase44e-{idx}-{period}"
        row["source_record_id"] = row["id"]
        row["fetched_at"] = "2026-10-07T03:20:00+00:00"
        row["promoted_at"] = "2026-10-07T03:21:00+00:00"
        row["promotion_run_id"] = "phase44e-test"
        if iid == "usd-vnd-central-rate":
            row["source_id"] = "vna-vietnamplus"
            row["corroboration_source_ids"] = ["vna-vietnamplus", "banking-times-vn"]
        else:
            row["source_id"] = "baonghean-gold"
            row["corroboration_source_ids"] = ["baonghean-gold", "vietnamnet-gold"]
        row["corroboration_observation_ids"] = [f"{row['id']}-a", f"{row['id']}-b"]
        row["evidence_status"] = "corroborated"
        row["observation_status"] = "final"
        rows.append(row)

    rows.sort(key=lambda r: (r.get("indicator_id", ""), r.get("period", ""), r.get("id", "")))
    incoming = {
        "schema_version": 1,
        "generated_at": "2026-10-07T03:21:00+00:00",
        "record_count": len(rows),
        "production_write": True,
        "repository_publish": False,
        "frontend_publish": False,
        "source_run_id": "phase44e-test",
        "data": rows,
    }
    run = {
        "schema_version": 1,
        "generated_at": "2026-10-07T03:21:00+00:00",
        "mode": "controlled-production-v1",
        "production_write": True,
        "repository_publish": False,
        "frontend_publish": False,
        "source_run_id": "phase44e-test",
        "prior_record_count": len(current["data"]),
        "added_record_count": 3,
        "unchanged_record_count": 0,
        "held_record_count": 0,
        "conflict_count": 0,
        "final_record_count": len(rows),
    }
    return incoming, run


def main():
    gate = load(ROOT / "config/daily_fx_gold_production_gate.json")
    policy = load(ROOT / "config/daily_auto_persistence_policy.json")
    assert set(gate["allowed_indicators"]) == DAILY_IDS
    assert set(policy["allowed_indicator_ids"]) == DAILY_IDS
    assert policy["max_additions_per_run"] == 3
    assert policy["on_source_failure"] == "retain-last-good"

    wf = (ROOT / ".github/workflows/macro-candidate.yml").read_text(encoding="utf-8")
    assert "daily-markets-production" in wf
    assert "--policy config/daily_fx_gold_production_gate.json" in wf
    assert "persist-daily-production:" in wf
    assert "python scripts/persist_daily_markets.py" in wf
    assert "contents: write" in wf
    assert "git push origin HEAD:main" in wf
    assert "15 3 * * *" in wf
    assert "15 9 * * 1-5" in wf
    assert "--source vietnamplus-central-rate" in wf
    assert "--source banking-times-central-rate" in wf
    assert "--source baonghean-gold" in wf
    assert "--source vietnamnet-gold" in wf

    current = load(ROOT / "data/processed/macro/observations.json")
    current_meta = load(ROOT / "data/processed/macro/repository-publish.json")
    incoming, run = make_incoming(current)

    tmp = Path(tempfile.mkdtemp(prefix="phase44e-"))
    try:
        repo = tmp / "repo"
        incoming_dir = tmp / "incoming"
        report = tmp / "report"
        dump(repo / "observations.json", current)
        dump(repo / "repository-publish.json", current_meta)
        dump(incoming_dir / "observations.json", incoming)
        dump(incoming_dir / "promotion-run.json", run)

        result = build_daily_persistence(
            incoming_dir,
            repo,
            report,
            source_run_number=max(99, int(current_meta.get("source_run_number", 0)) + 1),
            source_run_database_id="99999",
            auto_policy_path=ROOT / "config/daily_auto_persistence_policy.json",
            daily_gate_path=ROOT / "config/daily_fx_gold_production_gate.json",
            as_of=datetime(2026, 10, 7, 15, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
        )
        assert result["status"] == "ready-to-commit"
        assert result["added_record_count"] == 3
        out = load(repo / "observations.json")
        assert out["record_count"] == current["record_count"] + 3
        assert out["repository_publish"] is True
        assert out["repository_persistence_mode"] == "controlled-daily-auto-persistence-v1"
        assert {r["indicator_id"] for r in result["added"]} == DAILY_IDS

        # An unrelated addition must be blocked even if it looks final.
        bad_incoming = deepcopy(incoming)
        bad_run = deepcopy(run)
        bad = deepcopy(next(r for r in current["data"] if r["indicator_id"] == "cpi-yoy"))
        bad["period"] = "2026-10"
        bad["id"] = "phase44e-bad-monthly"
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
            build_daily_persistence(
                incoming2, repo2, report2,
                source_run_number=max(100, int(current_meta.get("source_run_number", 0)) + 2),
                source_run_database_id="100000",
                auto_policy_path=ROOT / "config/daily_auto_persistence_policy.json",
                daily_gate_path=ROOT / "config/daily_fx_gold_production_gate.json",
                as_of=datetime(2026, 10, 7, 15, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
            )
        except ValueError as exc:
            assert "exceed max" in str(exc) or "Non-daily indicator" in str(exc)
        else:
            raise AssertionError("Unrelated monthly addition was not blocked")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("Phase 4.4E daily Macro auto-publish tests PASS")


if __name__ == "__main__":
    main()
