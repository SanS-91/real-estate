"""Append only evidence-backed CBRE HCMC supply for newly published quarters.

Requires a release discovered on CBRE's index, a quarter in its article heading,
a published date, and an exact numeric phrase in the public article. Other metrics
and research sources remain manual-review-only.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/mock/market/observations.json"
CANDIDATES = ROOT / "data/candidate/market/observations.json"
COLLECTOR_REPORT = ROOT / "data/candidate/market/market-source-candidate-report.json"
REPORT = ROOT / "data/candidate/market/market-verified-metric-promotion-report.json"
SOURCES = ROOT / "data/mock/core/sources.json"
DISCOVERY_URL = "https://www.cbrevietnam.com/insights"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def release_identity(url):
    parsed = urlsplit(url or "")
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ("www.cbrevietnam.com", "cbrevietnam.com"):
        return None
    if parsed.query or parsed.fragment:
        return None
    path = parsed.path.rstrip("/")
    match = re.fullmatch(r"/insights/figures/ho-chi-minh-city-figures-q([1-4])-(20\d{2})", path.lower())
    if not match:
        return None
    return (f"{match.group(2)}-Q{match.group(1)}", f"https://www.cbrevietnam.com{path}")


def obs_key(row):
    return (
        row.get("scope_type"),
        tuple(row.get("region_ids") or []),
        tuple(row.get("segment_ids") or []),
        row.get("period"),
        row.get("source_id"),
    )


def assess(row, by_target, today, sources):
    identity = release_identity(row.get("source_url"))
    if not identity:
        return "not-approved-official-release"
    period, canonical_url = identity
    proof = row.get("source_verification") or {}
    digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]
    target_id = "cbre-discovered-" + digest
    source = by_target.get(target_id) or {}
    if source.get("status") != "parsed" or source.get("verified_source_period") != period:
        return "no-independent-collector-period-confirmation"
    if source.get("verified_source_date") != row.get("source_date"):
        return "source-date-not-verified"
    if source.get("source_period_evidence_url") != canonical_url:
        return "source-page-mismatch"
    if proof.get("discovery_url") != DISCOVERY_URL:
        return "missing-official-release-discovery"
    if proof.get("period") != period or proof.get("source_page") != canonical_url or not proof.get("publication_date_verified"):
        return "period-or-page-proof-mismatch"
    if row.get("period") != period or row.get("period_type") != "quarter":
        return "record-report-period-mismatch"
    if row.get("source_id") != "cbre-vietnam-market" or row.get("source_id") not in sources:
        return "source-not-approved"
    if row.get("scope_type") != "region-segment" or row.get("region_ids") != ["hcmc"]:
        return "wrong-market-scope"
    segments = row.get("segment_ids") or []
    if len(segments) != 1 or segments[0] not in ("apartment", "landed"):
        return "unsupported-segment"
    if row.get("id") != f"obs-hcmc-{segments[0]}-{period.lower()}-cbre":
        return "metric-id-mismatch"
    value = row.get("new_supply")
    if type(value) is not int or value <= 0:
        return "metric-not-strict-positive-integer"
    if any(row.get(k) is not None for k in ("sales_units", "absorption_rate", "average_asp")):
        return "other-metrics-not-approved"
    evidence = proof.get("metric_evidence") or ""
    if not evidence or not row.get("methodology_note", "").startswith(evidence):
        return "missing-verbatim-metric-evidence"
    mentioned = [int(re.sub(r"\D", "", x)) for x in re.findall(r"(?<![a-zA-Z])\d[\d.,]*", evidence)]
    if value not in mentioned:
        return "number-not-present-in-public-source-excerpt"
    try:
        pub = date.fromisoformat(row["source_date"])
        if pub > today.date() or pub.year < 2024:
            return "invalid-source-publication-date"
    except (TypeError, ValueError, KeyError):
        return "invalid-source-publication-date"
    return None


def prepare(existing, candidates, report, today, sources):
    by_target = {x.get("target_id"): x for x in report.get("targets", [])}
    old = {obs_key(x): x for x in existing}
    additions, decisions, seen = [], [], set()
    for row in candidates:
        key = obs_key(row)
        reason = assess(row, by_target, today, sources)
        if reason:
            decisions.append({"id":row.get("id"),"decision":"manual-review","reason":reason})
            continue
        if key in seen:
            decisions.append({"id":row.get("id"),"decision":"manual-review","reason":"duplicate-source-period"})
            continue
        seen.add(key)
        previous = old.get(key)
        if previous is not None:
            if previous.get("new_supply") == row["new_supply"]:
                decisions.append({"id":row["id"],"decision":"unchanged","reason":"quarter-already-recorded"})
            else:
                decisions.append({"id":row["id"],"decision":"manual-review","reason":"conflict-with-existing-history"})
            continue
        additions.append(copy.deepcopy(row))
        decisions.append({"id":row["id"],"decision":"new","reason":"verified-published-cbre-quarter"})
    return additions, decisions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["preview", "promote"], default="preview")
    args = ap.parse_args()
    production = load(OUTPUT)
    candidate = load(CANDIDATES)
    source_report = load(COLLECTOR_REPORT)
    sources = {x["id"] for x in load(SOURCES).get("data", [])}
    if candidate.get("candidate_only") is not True or candidate.get("record_count") != len(candidate.get("data", [])):
        raise SystemExit("Refuse publication: missing or invalid candidate manifest")
    if not any(x.get("index") == DISCOVERY_URL and x.get("status") == "discovered" for x in source_report.get("discovery", [])):
        raise SystemExit("Refuse publication: no verified CBRE index discovery")
    additions, decisions = prepare(
        production.get("data", []), candidate.get("data", []),
        source_report, datetime.now(timezone.utc), sources,
    )
    result = {
        "schema_version": 1, "mode": args.mode, "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_written": False, "eligible_new_metrics": len(additions),
        "manual_review": sum(x["decision"] == "manual-review" for x in decisions),
        "unchanged": sum(x["decision"] == "unchanged" for x in decisions),
        "decisions": decisions,
    }
    if args.mode == "promote" and additions:
        out = copy.deepcopy(production)
        out["data"] = sorted(
            out.get("data", []) + additions,
            key=lambda x: (x.get("scope_type") or "", x.get("period") or "", x.get("source_id") or "", x.get("id") or ""),
        )
        out["record_count"] = len(out["data"])
        out["generated_at"] = result["generated_at"]
        out["build_id"] = "market-verified-quarterly-supply-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        write(OUTPUT, out)
        result["production_written"] = True
        result["added_observations"] = len(additions)
    write(REPORT, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
