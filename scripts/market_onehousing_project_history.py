"""Phase 4I.3 — source-specific parent-project monthly OneHousing history.

New series can be onboarded from an already reviewed, monthly OneHousing
project reference + its exact configured URL. Never infer a new baseline,
average across subprojects, or promote a period without two publisher checks
on distinct GitHub Actions runs at least 60 minutes apart.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
import market_alternative_auto_probe as source

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/mock/market/alternative-price-evidence.json"
TARGETS = ROOT / "config/market-alternative-auto-targets.json"
HISTORY = ROOT / "data/mock/market/onehousing-project-monthly-history.json"
STATE = ROOT / "data/state/onehousing-project-monthly-verification.json"
REPORT = ROOT / "data/candidate/market/onehousing-project-monthly-release-report.json"
MAX_CHECKS = 12
MAX_CHANGE_PCT = 30.0


def load(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else copy.deepcopy(fallback)


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def series_key(row):
    return "onehousing-parent-" + row["project_id"] + "-apartment-popular-asking"


def monitored_pairs(evidence, targets):
    """No manual price numbers; every bootstrap is copied from reviewed evidence."""
    keys = {t["baseline_id"]: t for t in targets
            if t.get("mode") == "monthly-price-candidate"
            and t.get("source_id") == "onehousing-vn"
            and not t.get("subproject_name")}
    pairs = []
    for row in evidence:
        t = keys.get(row.get("id"))
        if (not t or not source.allowed_target(t) or
            row.get("project_id") != t.get("project_id") or
            row.get("source_url") != t.get("url") or
            row.get("source_id") != "onehousing-vn" or
            row.get("metric_type") != "popular-asking-price-per-sqm" or
            row.get("asset_type") != "apartment" or
            row.get("period_type") != "month" or
            not source.MONTH_LABEL.search(row.get("evidence", {}).get("period", "")) or
            not source.onehousing_monthly(
                "Biến động giá " + " ".join((
                    row.get("evidence", {}).get("period", ""),
                    "Đơn giá phổ biến Mức giá/ mét vuông xuất hiện nhiều nhất trong khoảng giá",
                    row.get("evidence", {}).get("metric", ""),
                    row.get("evidence", {}).get("range", ""),
                    "Giá thuê phổ biến",
                )),
                date.fromisoformat(row["review_date"]),
                t.get("publisher_project_name", "Vinhomes Grand Park")
            )):
            continue
        pairs.append((t, row))
    return pairs


def baseline_row(row):
    new = copy.deepcopy(row)
    new.update(
        series_key=series_key(row),
        source_record_id=row["id"],
        review_status="source-indexed-baseline",
        verification_mode="existing-reviewed-source-reference",
        methodology_note=(row.get("methodology_note", "") +
            " Historical series initialized from an existing reviewed evidence record. "
            "Not a newly captured publisher observation.")
    )
    return new


def signature(record, target):
    payload = [target["url"], target["project_id"], record["period"],
               record["value_vnd_per_m2"], record["range_low_vnd_per_m2"],
               record["range_high_vnd_per_m2"]]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def evaluate(rows, checks, base, target, parsed, access, checked, run_id):
    """Evaluate one source capture without HTTP/file side effects."""
    ident = series_key(base)
    existing = [r for r in rows if r.get("series_key") == ident]
    periods = {r["period"]: r for r in existing}
    if not existing or base["period"] not in periods:
        return checks, None, "missing-indexed-baseline"
    status = "source-unavailable"
    if parsed is not None:
        status = "matched-source-month-and-price" if access.get("http_status") == 200 else "source-access-invalid"
    elif access.get("status"):
        status = access["status"]
    if parsed and parsed["period"] in periods:
        published = periods[parsed["period"]]
        if all(parsed[k] == published.get(k) for k in
               ("value_vnd_per_m2", "range_low_vnd_per_m2", "range_high_vnd_per_m2")):
            status = "existing-month-unchanged"
        else:
            status = "source-revised-published-month"
    check = {
        "run_id": str(run_id), "checked_at": checked.isoformat(), "status": status,
        "period": parsed["period"] if parsed else None,
        "signature": signature(parsed, target) if parsed else None,
        "http_status": access.get("http_status"), "source_host": access.get("final_host")
    }
    if not any(x.get("run_id") == str(run_id) for x in checks):
        checks = (checks + [check])[-MAX_CHECKS:]
    if not parsed:
        return checks, None, "publisher-month-or-metric-unverifiable"
    if status == "source-revised-published-month":
        return checks, None, "source-revised-published-month"
    if parsed["period"] in periods:
        return checks, None, "already-in-source-history"
    if parsed["period"] <= max(periods):
        return checks, None, "out-of-order-source-month"
    previous = periods[max(periods)]
    if abs(parsed["value_vnd_per_m2"] / previous["value_vnd_per_m2"] - 1) * 100 > MAX_CHANGE_PCT:
        return checks, None, "price-jump-manual-review"
    last = checks[-2:]
    if len(last) < 2 or last[0]["run_id"] == last[1]["run_id"] or any(
        x.get("status") != "matched-source-month-and-price" or
        x.get("signature") != signature(parsed, target) or
        x.get("http_status") != 200 or
        x.get("source_host") not in {"onehousing.vn", "beta.onehousing.vn"}
        for x in last
    ):
        return checks, None, "need-two-consecutive-source-verifications"
    try:
        first, second = [datetime.fromisoformat(x["checked_at"]) for x in last]
        if first.tzinfo is None or second.tzinfo is None or second-first < timedelta(hours=1):
            return checks, None, "source-checks-under-one-hour"
    except (TypeError, KeyError, ValueError):
        return checks, None, "invalid-source-check-timestamps"
    new = {
        "id": target["target_id"] + "-" + parsed["period"],
        "project_id": base["project_id"],
        "source_id": base["source_id"], "source_url": base["source_url"],
        "metric_type": base["metric_type"], "asset_type": "apartment",
        "period_type": "month", "period": parsed["period"],
        "value_vnd_per_m2": parsed["value_vnd_per_m2"],
        "range_low_vnd_per_m2": parsed["range_low_vnd_per_m2"],
        "range_high_vnd_per_m2": parsed["range_high_vnd_per_m2"],
        "evidence": parsed["evidence"], "series_key": ident,
        "source_record_id": base["id"], "source_publication_date": None,
        "review_status": "automated-source-verified",
        "verification_mode": "two-independent-live-publisher-checks",
        "verification_run_ids": [x["run_id"] for x in last],
        "verified_at": checked.isoformat(),
        "methodology_note": "Original-source monthly modal apartment asking price, not a project-wide transacted ASP. Two independently matching OneHousing GitHub runs >=1 hour apart. Not combined with any subproject figures."
    }
    return checks, new, "verified-new-publisher-month"


def run(evidence, targets, history, previous, now, run_id, fetcher):
    pairs = monitored_pairs(evidence, targets)
    old = {x["series_key"]: x for x in previous.get("series", [])}
    rows = copy.deepcopy(history.get("data", []))
    states, decisions = [], []
    for target, base in pairs:
        ident = series_key(base)
        existing = [r for r in rows if r.get("series_key") == ident]
        if not existing:
            rows.append(baseline_row(base))
        access, html = fetcher(target)
        parsed = (source.onehousing_monthly(source.plain_text(html), now.date(),
                  target.get("publisher_project_name", "Vinhomes Grand Park"))
                  if html and access.get("http_status") == 200 else None)
        # Current-mode captures must be from exactly the configured source host.
        if access.get("final_host") not in ("onehousing.vn", "beta.onehousing.vn"):
            parsed = None
        checks, new, decision = evaluate(
            rows, old.get(ident, {}).get("checks", []),
            base, target, parsed, access, now, run_id)
        if new:
            rows.append(new)
        states.append({"series_key": ident, "project_id": base["project_id"],
                       "source_url": target["url"], "checks": checks,
                       "latest_decision": decision})
        decisions.append({"project_id": base["project_id"], "period": parsed["period"] if parsed else None,
                          "decision": decision, "released": bool(new)})
    return {
        **history, "schema_version": 1, "record_count": len(rows),
        "data": sorted(rows, key=lambda x: (x["series_key"], x["period"])),
        "collection_mode": "source-indexed-reference-plus-future-verified-months"
    }, {"schema_version": 1, "series": states}, decisions


def main():
    now = datetime.now(timezone.utc)
    evidence = load(EVIDENCE, {"data": []})["data"]
    targets = load(TARGETS, {"targets": []})["targets"]
    history = load(HISTORY, {"data": []})
    previous = load(STATE, {})
    session = requests.Session()
    output, state, decisions = run(
        evidence, targets, history, previous, now,
        os.environ.get("GITHUB_RUN_ID", now.isoformat()),
        lambda target: source.fetch_with_publisher_fallback(target, session))
    save(HISTORY, output)
    save(STATE, state)
    result = {"schema_version": 1, "generated_at": now.isoformat(),
              "series_count": len(state["series"]), "history_records": output["record_count"],
              "released_new_months": sum(d["released"] for d in decisions),
              "decisions": decisions}
    save(REPORT, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
