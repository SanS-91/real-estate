from pathlib import Path
import copy
import json
import shutil
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from persist_repository import build_repository_persistence  # noqa: E402

PERSISTENCE_POLICY = ROOT / "config/repository_persistence_policy.json"
PRODUCTION_POLICY = ROOT / "config/production_promotion_policy.json"


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def record(indicator_id: str, period: str, value: float, rid: str):
    return {
        "indicator_id": indicator_id,
        "period": period,
        "period_type": "month",
        "data_date": None,
        "value": value,
        "unit": "percent",
        "source_id": "nso-vietnam",
        "source_url": "https://example.test/nso-release",
        "published_at": "2026-10-03",
        "fetched_at": "2026-10-04T15:01:39+00:00",
        "evidence_status": "verified",
        "methodology_note": "fixture",
        "id": rid,
        "source_record_id": rid,
        "observation_status": "final",
        "promoted_at": "2026-10-04T15:02:39+00:00",
        "promotion_run_id": "20261004T150137Z",
    }


def make_artifact(path: Path, records: list[dict], prior_count: int, source_run_id: str = "20261004T150137Z"):
    dump(path / "observations.json", {
        "schema_version": 1,
        "generated_at": "2026-10-04T15:02:39+00:00",
        "record_count": len(records),
        "production_write": True,
        "repository_publish": False,
        "frontend_publish": False,
        "source_run_id": source_run_id,
        "data": records,
    })
    dump(path / "promotion-run.json", {
        "schema_version": 1,
        "generated_at": "2026-10-04T15:02:39+00:00",
        "mode": "controlled-production-v1",
        "production_write": True,
        "repository_publish": False,
        "frontend_publish": False,
        "source_run_id": source_run_id,
        "prior_record_count": prior_count,
        "added_record_count": max(0, len(records) - prior_count),
        "unchanged_record_count": min(prior_count, len(records)),
        "held_record_count": 0,
        "conflict_count": 0,
        "final_record_count": len(records),
        "added": [],
        "unchanged": [],
        "held": [],
    })


def call(incoming: Path, repo: Path, report: Path, run_number: int):
    return build_repository_persistence(
        incoming,
        repo,
        report,
        run_number,
        f"db-{run_number}",
        PERSISTENCE_POLICY,
        PRODUCTION_POLICY,
    )


def main():
    temp = Path(tempfile.mkdtemp(prefix="repository-persistence-test-"))
    try:
        repo = temp / "repo/data/processed/macro"
        report = temp / "report"
        incoming9 = temp / "incoming9"
        base = [
            record("core-cpi-yoy", "2026-09", 4.45, "id-core-sep"),
            record("cpi-mom", "2026-09", 0.62, "id-mom-sep"),
            record("cpi-yoy", "2026-09", 5.08, "id-yoy-sep"),
        ]
        make_artifact(incoming9, base, prior_count=0)

        # First manual persistence: append-only canonical records become repository state.
        r1 = call(incoming9, repo, report, 9)
        assert r1["status"] == "ready-to-commit", r1
        assert r1["added_record_count"] == 3, r1
        persisted = load(repo / "observations.json")
        assert persisted["record_count"] == 3
        assert persisted["repository_publish"] is True
        assert persisted["frontend_publish"] is False
        assert persisted["repository_source_run_number"] == 9
        meta = load(repo / "repository-publish.json")
        assert meta["source_run_number"] == 9
        assert meta["final_record_count"] == 3

        # Idempotency: same artifact creates no repository rewrite/commit expectation.
        before_obs = (repo / "observations.json").read_bytes()
        before_meta = (repo / "repository-publish.json").read_bytes()
        r2 = call(incoming9, repo, report, 9)
        assert r2["status"] == "no-change", r2
        assert r2["git_commit_expected"] is False
        assert (repo / "observations.json").read_bytes() == before_obs
        assert (repo / "repository-publish.json").read_bytes() == before_meta

        # Newer artifact may append a new period if it was built from current repository count.
        incoming10 = temp / "incoming10"
        extended = copy.deepcopy(base)
        extended.append(record("cpi-yoy", "2026-10", 4.90, "id-yoy-oct"))
        make_artifact(incoming10, extended, prior_count=3, source_run_id="20261104T010000Z")
        r3 = call(incoming10, repo, report, 10)
        assert r3["status"] == "ready-to-commit", r3
        assert r3["added_record_count"] == 1, r3
        assert load(repo / "observations.json")["record_count"] == 4

        # Historical mutation must be blocked.
        incoming11_bad = temp / "incoming11-bad"
        mutated = copy.deepcopy(extended)
        mutated[0]["value"] = 4.46
        make_artifact(incoming11_bad, mutated, prior_count=4, source_run_id="20261105T010000Z")
        try:
            call(incoming11_bad, repo, report, 11)
            raise AssertionError("Expected historical mutation to be blocked")
        except ValueError as exc:
            assert "Historical mutation" in str(exc), exc

        # Record drop must be blocked.
        incoming11_drop = temp / "incoming11-drop"
        dropped = copy.deepcopy(extended[:-1])
        make_artifact(incoming11_drop, dropped, prior_count=4, source_run_id="20261105T020000Z")
        try:
            call(incoming11_drop, repo, report, 11)
            raise AssertionError("Expected record drop to be blocked")
        except ValueError as exc:
            assert "Record-drop" in str(exc) or "stale" in str(exc).lower(), exc

        # An older run cannot change repository state after a newer run has been persisted.
        incoming8 = temp / "incoming8"
        older_change = copy.deepcopy(extended)
        older_change.append(record("cpi-mom", "2026-10", 0.30, "id-mom-oct"))
        make_artifact(incoming8, older_change, prior_count=4, source_run_id="20261103T010000Z")
        try:
            call(incoming8, repo, report, 8)
            raise AssertionError("Expected older source run to be blocked")
        except ValueError as exc:
            assert "older than last persisted" in str(exc), exc

        print("Repository persistence tests passed")
    finally:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    main()
