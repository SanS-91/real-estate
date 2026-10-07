from __future__ import annotations

from copy import deepcopy
from pathlib import Path
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


def latest_daily_period(payload: dict) -> str:
    periods = [
        r.get("period")
        for r in payload.get("data", [])
        if r.get("indicator_id") in DAILY_IDS and r.get("period_type") == "day" and r.get("period")
    ]
    assert periods, "Daily FX/gold repository baseline is missing"
    return max(periods)


def test_data_classification_and_docs_are_not_globally_mock():
    settings = load(ROOT / "config/settings.json")
    meta = load(ROOT / "data/mock/core/meta.json")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    provenance = (ROOT / "assets/js/provenance.js").read_text(encoding="utf-8")

    assert settings["data_root"] == "./data/mock/"
    assert settings["data_mode"] == "hybrid-curated-production"
    assert settings["static_root_legacy_name"] is True
    assert meta["is_mock"] is False
    assert meta["data_mode"] == "hybrid-curated-production"
    assert "All current values, dates and developments are illustrative mock data only." not in readme
    assert "All current datasets remain illustrative mock data." not in readme
    assert "No live source URL in the illustrative demo registry" not in provenance
    assert "Phase 4.4F — Production Hardening Baseline" in readme


def test_committed_update_status_matches_current_daily_repository():
    repo = load(ROOT / "data/processed/macro/observations.json")
    status = load(ROOT / "data/state/update-status.json")
    row = next(r for r in status["datasets"] if r["id"] == "macro-daily-markets")
    expected_period = latest_daily_period(repo)
    expected_count = sum(
        1 for r in repo["data"]
        if r.get("indicator_id") in DAILY_IDS
    )

    assert row["latest_observation_period"] == expected_period
    assert row["record_count"] == expected_count
    assert row["last_updated_at"] == repo["generated_at"]


def test_github_actions_are_pinned_to_node24_compatible_majors():
    workflows = list((ROOT / ".github/workflows").glob("*.yml"))
    assert workflows
    combined = "\n".join(p.read_text(encoding="utf-8") for p in workflows)

    assert "runs-on: ubuntu-latest" not in combined
    assert "runs-on: ubuntu-24.04" in combined
    assert "actions/checkout@v4" not in combined
    assert "actions/setup-python@v5" not in combined
    assert "actions/upload-artifact@v4" not in combined
    assert "actions/download-artifact@v4" not in combined
    assert "actions/cache@v4" not in combined

    assert "actions/checkout@v7" in combined
    assert "actions/setup-python@v7" in combined
    assert "actions/upload-artifact@v7" in combined
    assert "actions/download-artifact@v7" in combined
    assert "actions/cache@v6" in combined


def test_daily_persistence_is_idempotent_for_current_repository():
    current = load(ROOT / "data/processed/macro/observations.json")
    current_meta = load(ROOT / "data/processed/macro/repository-publish.json")

    incoming = deepcopy(current)
    incoming["repository_publish"] = False
    incoming["frontend_publish"] = False
    incoming.pop("repository_published_at", None)
    incoming.pop("repository_source_run_number", None)
    incoming.pop("repository_source_run_database_id", None)
    incoming.pop("repository_persistence_mode", None)

    run = {
        "schema_version": 1,
        "generated_at": incoming.get("generated_at"),
        "mode": "controlled-production-v1",
        "production_write": True,
        "repository_publish": False,
        "frontend_publish": False,
        "source_run_id": incoming.get("source_run_id"),
        "prior_record_count": len(current["data"]),
        "added_record_count": 0,
        "unchanged_record_count": 3,
        "held_record_count": 0,
        "conflict_count": 0,
        "final_record_count": len(current["data"]),
    }

    tmp = Path(tempfile.mkdtemp(prefix="phase44f-"))
    try:
        repo = tmp / "repo"
        incoming_dir = tmp / "incoming"
        report = tmp / "report"
        dump(repo / "observations.json", current)
        dump(repo / "repository-publish.json", current_meta)
        dump(incoming_dir / "observations.json", incoming)
        dump(incoming_dir / "promotion-run.json", run)

        before = (repo / "observations.json").read_bytes()
        result = build_daily_persistence(
            incoming_dir,
            repo,
            report,
            source_run_number=int(current_meta.get("source_run_number", 0)) + 1,
            source_run_database_id="phase44f-idempotency",
            auto_policy_path=ROOT / "config/daily_auto_persistence_policy.json",
            daily_gate_path=ROOT / "config/daily_fx_gold_production_gate.json",
        )
        after = (repo / "observations.json").read_bytes()

        assert result["status"] == "no-change"
        assert result["added_record_count"] == 0
        assert result["final_record_count"] == len(current["data"])
        assert before == after
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
