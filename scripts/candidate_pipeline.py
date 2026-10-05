from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
from typing import Any

from collectors.base import build_session, fetch_html

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MAP = {
    "nso-cpi": "nso_cpi_sample.html",
    "sbv-central-rate": "sbv_sample.html",
    "sjc-gold": "sjc_sample.html",
    "vov-central-rate": "vov_sample.html",
    "vietcap-macro": "vietcap_sample.html",
    "vietnamplus-cpi": "vietnamplus_cpi_sample.html",
    "vietnamplus-central-rate": "vietnamplus_central_rate_sample.html",
    "pnj-gold": "pnj_gold_sample.html",
    "doji-gold": "doji_gold_sample.html",
    "baonghean-gold": "baonghean_gold_sample.html",
    "banking-times-central-rate": "thoibaonganhang_central_rate_sample.html",
    "vietnamnet-gold": "vietnamnet_gold_sample.html",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid(*parts: Any) -> str:
    raw = "|".join(str(x or "") for x in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_sources(selected: list[str] | None):
    cfg = read_json(ROOT / "config/live_sources.json")
    sources = [x for x in cfg["sources"] if x.get("enabled", True)]
    if selected:
        wanted = set(selected)
        unknown = wanted - {x["key"] for x in sources}
        if unknown:
            raise SystemExit(f"Unknown source(s): {', '.join(sorted(unknown))}")
        sources = [x for x in sources if x["key"] in wanted]
    return sources


def parse_result(result, source_cfg, source_url, fetched_at):
    observations, research = [], []
    if isinstance(result, list):
        for x in result:
            if not isinstance(x, dict):
                continue
            x = dict(x)
            x.setdefault("source_id", source_cfg["source_id"])
            x.setdefault("source_url", source_url)
            x.setdefault("fetched_at", fetched_at)
            x["id"] = x.get("id") or uid(
                x.get("indicator_id"), x.get("period"), x.get("data_date"),
                x.get("source_id"), x.get("value"), x.get("unit")
            )
            observations.append(x)
    elif isinstance(result, dict):
        x = dict(result)
        x.setdefault("source_id", source_cfg["source_id"])
        x.setdefault("source_url", source_url)
        x.setdefault("fetched_at", fetched_at)
        x["id"] = x.get("id") or uid(x.get("source_id"), x.get("title"), x.get("published_at"), x.get("source_url"))
        research.append(x)
    return observations, research


def merge_records(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Merge by stable ID. Incoming replaces same ID; historical IDs remain."""
    out = {x["id"]: x for x in existing if isinstance(x, dict) and x.get("id")}
    for x in incoming:
        out[x["id"]] = x
    return sorted(out.values(), key=lambda r: (
        r.get("indicator_id") or "",
        r.get("period") or r.get("data_date") or r.get("published_at") or "",
        r.get("source_id") or "",
        r.get("id") or "",
    ))


def fetch_source(source_cfg: dict, run_id: str, fixture_mode: bool):
    key = source_cfg["key"]
    module = importlib.import_module(source_cfg["module"])
    parser = getattr(module, source_cfg["parser"])
    raw_root = ROOT / "data/raw/live" / key / run_id
    raw_root.mkdir(parents=True, exist_ok=True)

    if fixture_mode:
        fixture = ROOT / "tests/fixtures" / FIXTURE_MAP[key]
        html = fixture.read_text(encoding="utf-8")
        fetched_at = now_iso()
        source_url = f"https://fixture.local/{key}"
        result = parser(html, source_url, fetched_at)
        obs, res = parse_result(result, source_cfg, source_url, fetched_at)
        return obs, res, {
            "source": key, "status": "healthy", "fixture_mode": True,
            "records": len(obs) + len(res), "parsed_observations": len(obs),
            "parsed_research": len(res), "target_url": source_url,
            "final_url": source_url, "content_hash": hashlib.sha256(html.encode()).hexdigest(),
            "fetched_at": fetched_at, "elapsed_ms": 0,
        }

    session = build_session()
    target_url = source_cfg.get("fetch_url")
    landing_meta = None
    if source_cfg.get("discoverer"):
        landing_url = source_cfg["landing_url"]
        landing = fetch_html(
            landing_url,
            timeout=source_cfg.get("timeout_seconds", 30),
            max_bytes=source_cfg.get("max_bytes", 5_000_000),
            session=session,
        )
        (raw_root / "landing.html").write_text(landing.text, encoding="utf-8")
        discover = getattr(module, source_cfg["discoverer"])
        target_url = discover(landing.text, landing.url)
        landing_meta = {
            "url": landing.url,
            "content_hash": landing.content_hash,
            "fetched_at": landing.fetched_at,
            "elapsed_ms": landing.elapsed_ms,
        }
        if not target_url:
            raise ValueError(f"Discovery returned no detail URL from {landing.url}")

    if not target_url:
        raise ValueError("No fetch_url or discovered target URL configured")

    fr = fetch_html(
        target_url,
        timeout=source_cfg.get("timeout_seconds", 30),
        max_bytes=source_cfg.get("max_bytes", 5_000_000),
        session=session,
    )
    (raw_root / "detail.html").write_text(fr.text, encoding="utf-8")
    result = parser(fr.text, fr.url, fr.fetched_at)
    obs, res = parse_result(result, source_cfg, fr.url, fr.fetched_at)
    total = len(obs) + len(res)
    min_records = int(source_cfg.get("min_records", 0))
    max_records = int(source_cfg.get("max_records", 999999))
    if total < min_records:
        raise ValueError(f"Parsed {total} records; expected at least {min_records}")
    if total > max_records:
        raise ValueError(f"Parsed {total} records; expected at most {max_records}")

    return obs, res, {
        "source": key, "status": "healthy", "fixture_mode": False,
        "records": total, "parsed_observations": len(obs), "parsed_research": len(res),
        "target_url": target_url, "final_url": fr.url,
        "content_hash": fr.content_hash, "content_type": fr.content_type,
        "etag": fr.etag, "last_modified": fr.last_modified,
        "fetched_at": fr.fetched_at, "elapsed_ms": fr.elapsed_ms,
        "landing": landing_meta,
    }


def validate_records(obs_payload: dict, research_payload: dict):
    from jsonschema import Draft202012Validator, FormatChecker
    problems = []
    for payload, schema_name, label in [
        (obs_payload, "macro_observation.schema.json", "observation"),
        (research_payload, "research_evidence.schema.json", "research"),
    ]:
        schema = read_json(ROOT / "schemas" / schema_name)
        v = Draft202012Validator(schema, format_checker=FormatChecker())
        for i, item in enumerate(payload.get("data", [])):
            for err in v.iter_errors(item):
                problems.append(f"{label} row {i}: {err.message}")
    return problems


def _latest_key(r: dict):
    return (
        r.get("data_date") or r.get("period") or "",
        r.get("published_at") or "",
        r.get("fetched_at") or "",
    )


def _same_observation(a: dict, b: dict, tolerance: float) -> bool:
    if a.get("indicator_id") != b.get("indicator_id"):
        return False
    # Compare the same business period/date when both are available.
    da = a.get("data_date") or a.get("period")
    db = b.get("data_date") or b.get("period")
    if da and db and da != db:
        return False
    try:
        return abs(float(a.get("value")) - float(b.get("value"))) <= tolerance
    except Exception:
        return False


def build_publish_readiness(observations: list[dict], generated_at: str):
    indicators = {x["id"]: x for x in read_json(ROOT / "config/macro_indicators_live.json")["indicators"]}
    pool_cfg = read_json(ROOT / "config/source_pools.json", {"pools": []})
    pool_by_indicator = {}
    for pool in pool_cfg.get("pools", []):
        for iid in pool.get("indicator_ids", []):
            pool_by_indicator[iid] = pool

    by_ind = {}
    for x in observations:
        by_ind.setdefault(x.get("indicator_id"), []).append(x)

    results = []
    pool_summaries = []
    for iid, meta in indicators.items():
        rows = by_ind.get(iid, [])
        pool = pool_by_indicator.get(iid, {})
        preferred = pool.get("preferred_source_ids") or [meta.get("primary_source_id")]
        fallback = pool.get("fallback_source_ids", [])
        canonical_statuses = set(pool.get("canonical_evidence_status", ["verified"]))
        tolerance = float(pool.get("corroboration_tolerance_abs", 0))
        min_sources = int(pool.get("min_independent_sources_for_corroborated", 2))

        canonical = [r for r in rows if r.get("source_id") in preferred and r.get("evidence_status") in canonical_statuses]
        if canonical:
            selected = sorted(canonical, key=_latest_key)[-1]
            results.append({
                "indicator_id": iid, "status": "ready-canonical",
                "selected_observation_id": selected["id"],
                "evidence_observation_ids": [r["id"] for r in rows],
                "reason": f"Verified preferred-source observation from {selected.get('source_id')}.",
            })
            continue

        eligible = [r for r in rows if r.get("source_id") in fallback and r.get("evidence_status") not in {"disputed", "superseded"}]
        corroborated_group = []
        if eligible:
            # Evaluate only the latest business period/date, then choose the largest
            # agreement cluster. This prevents a single newly-fetched outlier from
            # overriding two independent sources that agree with each other.
            latest_business_period = max((r.get("data_date") or r.get("period") or "") for r in eligible)
            latest_rows = [r for r in eligible if (r.get("data_date") or r.get("period") or "") == latest_business_period]
            groups = []
            for anchor in latest_rows:
                group = [r for r in latest_rows if _same_observation(anchor, r, tolerance)]
                sources = {r.get("source_id") for r in group if r.get("source_id")}
                groups.append((len(sources), group))
            groups.sort(key=lambda item: item[0], reverse=True)
            corroborated_group = groups[0][1] if groups else []

            source_rank = {sid: idx for idx, sid in enumerate(fallback)}
            independent_sources = sorted(
                {r.get("source_id") for r in corroborated_group if r.get("source_id")},
                key=lambda sid: (source_rank.get(sid, 10_000), sid),
            )
            if len(independent_sources) >= min_sources:
                selected_source = independent_sources[0]
                source_rows = [r for r in corroborated_group if r.get("source_id") == selected_source]
                selected = sorted(source_rows, key=_latest_key)[-1]
                ordered_evidence = sorted(
                    corroborated_group,
                    key=lambda r: (source_rank.get(r.get("source_id"), 10_000), r.get("source_id") or "", _latest_key(r)),
                )
                results.append({
                    "indicator_id": iid, "status": "ready-corroborated",
                    "selected_observation_id": selected["id"],
                    "evidence_observation_ids": [r["id"] for r in ordered_evidence],
                    "independent_sources": independent_sources,
                    "latest_business_period": latest_business_period,
                    "reason": f"{len(independent_sources)} independent fallback sources agree for latest period {latest_business_period} within tolerance {tolerance}.",
                })
                continue
            # Stay on the latest business period even when corroboration is not yet deep enough.
            # Older, better-corroborated dates remain in candidate history but must not become
            # the current evidence selection for a daily indicator.
            latest_source_rank = {sid: idx for idx, sid in enumerate(fallback)}
            ordered_latest = sorted(
                latest_rows,
                key=lambda r: (latest_source_rank.get(r.get("source_id"), 10_000), r.get("source_id") or "", _latest_key(r)),
            )
            selected = ordered_latest[0] if ordered_latest else None
            results.append({
                "indicator_id": iid, "status": "evidence-only",
                "selected_observation_id": selected["id"] if selected else None,
                "evidence_observation_ids": [r["id"] for r in ordered_latest],
                "independent_sources": sorted({r.get("source_id") for r in latest_rows if r.get("source_id")}),
                "latest_business_period": latest_business_period,
                "reason": f"Latest period {latest_business_period} has fallback evidence, but direct verification or independent corroboration threshold is not met.",
            })
        elif rows:
            results.append({
                "indicator_id": iid, "status": "evidence-only",
                "selected_observation_id": None,
                "evidence_observation_ids": [r["id"] for r in rows],
                "reason": "Candidate observations exist outside configured preferred/fallback source pool.",
            })
        else:
            results.append({
                "indicator_id": iid, "status": "missing",
                "selected_observation_id": None,
                "reason": "No candidate observation available.",
            })

    for pool in pool_cfg.get("pools", []):
        statuses = [x for x in results if x["indicator_id"] in pool.get("indicator_ids", [])]
        available = [x for x in statuses if x["status"] != "missing"]
        pool_summaries.append({
            "pool_id": pool["id"],
            "indicator_count": len(statuses),
            "available_indicator_count": len(available),
            "coverage_status": "available" if available else "unavailable",
            "indicator_statuses": {x["indicator_id"]: x["status"] for x in statuses},
        })

    return {
        "generated_at": generated_at,
        "production_publish": False,
        "data": results,
        "pools": pool_summaries,
    }

def write_summary_csv(path: Path, observations: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["indicator_id", "period", "data_date", "value", "unit", "source_id", "evidence_status", "published_at", "source_url"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for x in observations:
            w.writerow({k: x.get(k) for k in cols})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="candidate", choices=["candidate"])
    ap.add_argument("--source", action="append", help="Source key; repeatable. Default = all enabled sources.")
    ap.add_argument("--fixture-mode", action="store_true", help="Use local parser fixtures; no network.")
    ap.add_argument("--replace-history", action="store_true", help="Do not merge prior candidate history.")
    ap.add_argument("--output-root", help="Alternative candidate output root for tests/review.")
    args = ap.parse_args()

    safety = read_json(ROOT / "config/candidate_safety.json")
    if safety.get("production_publish") is not False:
        raise SystemExit("Safety violation: production_publish must remain false in Phase 4.2B")

    sources = load_sources(args.source)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    generated_at = now_iso()
    output_root = Path(args.output_root) if args.output_root else ROOT / "data/candidate/macro"
    output_root.mkdir(parents=True, exist_ok=True)
    prior_obs = read_json(output_root / "observations.json", {"data": []}).get("data", []) if not args.replace_history else []
    prior_res = read_json(output_root / "research-evidence.json", {"data": []}).get("data", []) if not args.replace_history else []

    run_obs, run_res, health = [], [], []
    hard_failures = []
    for src in sources:
        try:
            obs, res, h = fetch_source(src, run_id, args.fixture_mode)
            run_obs.extend(obs); run_res.extend(res); health.append(h)
        except Exception as exc:
            status = "degraded" if src.get("optional") else "failed"
            health.append({
                "source": src["key"], "status": status, "optional": bool(src.get("optional")),
                "records": 0, "error": f"{type(exc).__name__}: {exc}", "checked_at": now_iso(),
            })
            if not src.get("optional"):
                hard_failures.append(src["key"])

    merged_obs = merge_records(prior_obs, run_obs)
    merged_res = merge_records(prior_res, run_res)
    obs_payload = {"schema_version": 1, "generated_at": generated_at, "record_count": len(merged_obs), "candidate_only": True, "data": merged_obs}
    res_payload = {"schema_version": 1, "generated_at": generated_at, "record_count": len(merged_res), "candidate_only": True, "data": merged_res}
    validation_errors = validate_records(obs_payload, res_payload)

    # Safety gates. Hard source failures make the run degraded, but do not erase previous good candidate history.
    prior_count = len(prior_obs)
    current_count = len(merged_obs)
    drop_pct = 0 if prior_count == 0 else max(0.0, (prior_count - current_count) / prior_count * 100.0)
    gate_errors = list(validation_errors)
    if not safety.get("allow_empty_candidate") and current_count == 0:
        gate_errors.append("Candidate observation set is empty.")
    if drop_pct > float(safety.get("max_total_record_drop_pct", 60)):
        gate_errors.append(f"Observation count dropped {drop_pct:.1f}% vs prior candidate.")

    run_status = "pass" if not gate_errors else "blocked"
    if hard_failures and run_status == "pass":
        run_status = "degraded"

    readiness = build_publish_readiness(merged_obs, generated_at)
    pool_coverage = readiness.get("pools", [])
    unavailable_pools = [x["pool_id"] for x in pool_coverage if x.get("coverage_status") == "unavailable"]
    if unavailable_pools and run_status == "pass":
        run_status = "degraded"
    source_health = {
        "schema_version": 1, "generated_at": generated_at, "run_id": run_id,
        "candidate_only": True, "sources": health,
        "healthy": sum(1 for x in health if x.get("status") == "healthy"),
        "degraded": sum(1 for x in health if x.get("status") == "degraded"),
        "failed": sum(1 for x in health if x.get("status") == "failed"),
    }
    report = {
        "schema_version": 1, "run_id": run_id, "generated_at": generated_at,
        "mode": "candidate", "fixture_mode": args.fixture_mode,
        "production_publish": False, "status": run_status,
        "selected_sources": [x["key"] for x in sources],
        "new_observations": len(run_obs), "new_research_evidence": len(run_res),
        "candidate_observations_total": current_count,
        "candidate_research_total": len(merged_res),
        "prior_observation_count": prior_count, "record_drop_pct": round(drop_pct, 2),
        "hard_source_failures": hard_failures,
        "unavailable_sources": [x.get("source") for x in health if x.get("status") in {"failed", "degraded", "unavailable"}],
        "unavailable_pools": unavailable_pools,
        "pool_coverage": pool_coverage,
        "source_errors": [
            {"source": x.get("source"), "status": x.get("status"), "error": x.get("error")}
            for x in health if x.get("error")
        ],
        "validation_errors": validation_errors, "gate_errors": gate_errors,
    }

    # Build into a repository-local temp directory, then atomically replace candidate files
    # only when schema/safety gates pass. GitHub runners start from a clean checkout, so
    # the parent directory must be created explicitly before tempfile.mkdtemp(..., dir=...).
    dist_root = ROOT / "dist"
    dist_root.mkdir(parents=True, exist_ok=True)
    build_dir = Path(tempfile.mkdtemp(prefix="macro-candidate-", dir=str(dist_root)))
    try:
        write_json(build_dir / "observations.json", obs_payload)
        write_json(build_dir / "research-evidence.json", res_payload)
        write_json(build_dir / "publish-readiness.json", readiness)
        write_json(build_dir / "source-health.json", source_health)
        write_json(build_dir / "run-report.json", report)
        write_summary_csv(build_dir / "candidate-summary.csv", merged_obs)

        if gate_errors:
            reject = ROOT / "data/rejected/macro" / run_id
            reject.mkdir(parents=True, exist_ok=True)
            for p in build_dir.iterdir():
                shutil.copy2(p, reject / p.name)

            # Blocked live runs remain reviewable in candidate mode. Never replace
            # observation/research history when safety gates fail. Only update run
            # metadata so GitHub Actions can finish and upload the diagnostics.
            for name in ["run-report.json", "source-health.json", "publish-readiness.json", "candidate-summary.csv"]:
                srcp = build_dir / name
                if srcp.exists():
                    tmp_target = output_root / (name + ".tmp")
                    shutil.copy2(srcp, tmp_target)
                    os.replace(tmp_target, output_root / name)

            print(json.dumps(report, ensure_ascii=False, indent=2))
            # Schema errors indicate an implementation defect and still fail CI.
            # Missing/unavailable live sources are recorded as status=blocked without
            # any production/candidate-history mutation.
            if validation_errors:
                raise SystemExit(2)
            return

        # Atomic per-file replacement; production files are intentionally not present in this package.
        for p in build_dir.iterdir():
            tmp_target = output_root / (p.name + ".tmp")
            shutil.copy2(p, tmp_target)
            os.replace(tmp_target, output_root / p.name)

        # Persist source-state metadata for optional GitHub Actions cache.
        state = {"schema_version": 1, "updated_at": generated_at, "run_id": run_id, "sources": health}
        write_json(ROOT / "data/state/source-state.json", state)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
