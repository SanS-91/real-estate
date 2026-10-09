"""Source-evidence gate for manually verified historical Market observations.

A curated historical release is never estimated from adjacent quarters. Publisher
methodologies, reporting geographies and periods remain distinct. Promotion is
append-only; source conflicts are rejected rather than silently overwritten.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/market-history-expansion-20261009.json"
PRODUCTION = ROOT / "data/mock/market/observations.json"
SOURCES = ROOT / "data/mock/core/sources.json"
CANDIDATE = ROOT / "data/candidate/market/history-expansion-candidates.json"
REPORT = ROOT / "data/candidate/market/history-expansion-report.json"

HOST_ALLOWLIST = {
    "cbre-vietnam-market": ("cbrevietnam.com",),
    "cushman-wakefield-vietnam-market": ("cushmanwakefield.com", "assets.cushmanwakefield.com"),
    "savills-vietnam-market": ("savills.com", "savills.com.vn"),
}
PERIODS = {
    "quarter": re.compile(r"^(20\d\d)-Q[1-4]$"),
    "half-year": re.compile(r"^(20\d\d)-H[12]$"),
    "year": re.compile(r"^(20\d\d)$"),
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def key(row):
    return (
        row.get("scope_type"),
        tuple(row.get("region_ids") or []),
        tuple(row.get("segment_ids") or []),
        row.get("period"),
        row.get("source_id"),
    )


def end_of_reporting_period(period, period_type):
    year = int(period[:4])
    if period_type == "year":
        return date(year, 12, 31)
    if period_type == "half-year":
        return date(year, 6 if period.endswith("H1") else 12, 30 if period.endswith("H1") else 31)
    month = int(period[-1]) * 3
    return date(year, month, 31 if month in (3,12) else 30)


def source_value_in_evidence(field, value, evidence):
    text = str(evidence.get(field) or "")
    if not text:
        return False
    tokens = re.findall(r"(?<!\d)\d[\d,]*(?:\.\d+)?", text)
    nums = set()
    for token in tokens:
        try:
            nums.add(float(token.replace(",", "")))
        except ValueError:
            pass
    expected = value * 100 if field == "absorption_rate" else value
    return float(expected) in nums


def validate(row, sources, today):
    issues = []
    for f in ("id", "scope_type", "period", "period_type", "source_id", "source_date", "source_url", "methodology_note"):
        if not row.get(f):
            issues.append("missing-" + f)
    if row.get("source_id") not in sources:
        issues.append("unregistered-source")
    host = (urlparse(row.get("source_url") or "").hostname or "").lower()
    if urlparse(row.get("source_url") or "").scheme != "https" or not any(
        host == allowed or host.endswith("." + allowed)
        for allowed in HOST_ALLOWLIST.get(row.get("source_id"), ())
    ):
        issues.append("source-url-not-on-publisher-host")
    period_type = row.get("period_type")
    period = str(row.get("period") or "")
    if not PERIODS.get(period_type, re.compile(r"^$")).fullmatch(period):
        issues.append("invalid-period-type-or-format")
    try:
        source_date = date.fromisoformat(row.get("source_date") or "")
        if source_date > today:
            issues.append("publication-in-the-future")
        if PERIODS.get(period_type) and PERIODS[period_type].fullmatch(period):
            if source_date < end_of_reporting_period(period, period_type):
                issues.append("publication-before-reporting-period-ended")
    except ValueError:
        issues.append("invalid-source-date")
    if row.get("region_ids") != ["hcmc"]:
        issues.append("unsupported-geography")
    if row.get("reported_geography") != "former-hcmc-core":
        issues.append("missing-source-geography-scope")
    if not isinstance(row.get("segment_ids"), list) or len(row["segment_ids"]) != 1 or row["segment_ids"][0] not in ("apartment", "landed", "residential"):
        issues.append("unsupported-segment")
    if row.get("scope_type") not in ("region-segment", "region-segment-benchmark"):
        issues.append("unsupported-scope")
    if period_type != "quarter" and row.get("scope_type") != "region-segment-benchmark":
        issues.append("year-and-h1-must-be-benchmarks")
    if row.get("reporting_basis") == "combined-apartment-and-landed":
        if row.get("segment_ids") != ["residential"] or row.get("scope_type") != "region-segment-benchmark":
            issues.append("combined-units-must-not-be-assigned-to-apartments")
    if row.get("scope_type") == "region-segment" and period_type != "quarter":
        issues.append("quarter-series-requires-quarter-period")
    evidence = row.get("source_evidence") or {}
    nonempty = 0
    for field in ("new_supply", "sales_units", "absorption_rate", "reported_primary_price_usd_per_sqm"):
        value = row.get(field)
        if value is None:
            continue
        nonempty += 1
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            issues.append("invalid-" + field)
            continue
        if field == "absorption_rate" and value > 1:
            issues.append("invalid-absorption-percentage")
        elif field != "absorption_rate" and int(value) != value:
            issues.append("non-integer-unit-count-or-usd-sqm")
        if not source_value_in_evidence(field, value, evidence):
            issues.append("metric-not-in-source-evidence-" + field)
    if nonempty == 0:
        issues.append("empty-source-observation")
    if row.get("average_asp") is not None:
        issues.append("unverified-vnd-price-must-stay-null")
    if row.get("sales_units") is not None and row.get("absorption_rate") is not None:
        # The original research denominator can include standing inventory.
        # Never equate sales/new launches with the source-stated absorption %.
        if "absorption" not in str(row.get("methodology_note", "")).lower():
            issues.append("absorption-denominator-not-explained")
    qualifiers = row.get("metric_qualifiers") or {}
    if any(k not in ("new_supply", "sales_units", "absorption_rate") or v not in ("approx", "lower-bound") for k,v in qualifiers.items()):
        issues.append("invalid-qualifier")
    if row.get("reported_primary_price_usd_per_sqm") is not None and not row.get("reported_primary_price_area_basis"):
        issues.append("missing-original-price-area-basis")
    return issues


def stage(records, production, sources, today):
    seen_id, seen_key = set(), set()
    old_by_key = {key(x): x for x in production}
    old_ids = {x.get("id") for x in production}
    conflicts, decisions, new = [], [], []
    for row in records:
        issues = validate(row, sources, today)
        item_key = key(row)
        if row.get("id") in seen_id:
            issues.append("duplicate-id-in-staging")
        if item_key in seen_key:
            issues.append("duplicate-source-period-in-staging")
        seen_id.add(row.get("id"))
        seen_key.add(item_key)
        prior = old_by_key.get(item_key)
        if prior:
            comparable_fields = (
                "new_supply", "sales_units", "absorption_rate", "average_asp",
                "metric_qualifiers", "reported_primary_price_usd_per_sqm",
            )
            if any(row.get(f) != prior.get(f) for f in comparable_fields):
                issues.append("conflicting-existing-observation")
            elif row.get("id") != prior.get("id"):
                issues.append("same-observation-under-different-id")
        elif row.get("id") in old_ids:
            issues.append("observation-id-collides-with-different-record")
        status = "blocked" if issues else ("unchanged" if prior else "new")
        decisions.append({
            "id": row.get("id"), "source_id": row.get("source_id"),
            "period": row.get("period"), "status": status, "issues": issues,
        })
        if issues:
            conflicts.append({"id": row.get("id"), "issues": issues})
        elif status == "new":
            new.append(copy.deepcopy(row))
    return new, decisions, conflicts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preview", "promote"), default="preview")
    args = parser.parse_args()
    cfg = load(CONFIG)
    original = load(PRODUCTION)
    sources = {x["id"] for x in load(SOURCES)["data"]}
    now = datetime.now(timezone.utc)
    new, decisions, conflicts = stage(cfg["records"], original["data"], sources, now.date())
    report = {
        "schema_version": 1, "generated_at": now.isoformat(),
        "mode": args.mode, "source_checked": len(cfg["records"]),
        "eligible": len(new), "unchanged": sum(d["status"] == "unchanged" for d in decisions),
        "blocked": len(conflicts), "production_written": False,
        "decisions": decisions, "conflicts": conflicts,
        "comment": "Curated official publisher releases only. No absent quarters or FX prices inferred."
    }
    dump(CANDIDATE, {
        "schema_version": 1, "candidate_only": True, "generated_at": now.isoformat(),
        "record_count": len(new), "data": new,
    })
    if args.mode == "promote" and not conflicts and new:
        promoted = copy.deepcopy(original)
        promoted["data"] += new
        promoted["data"].sort(key=lambda x:(x.get("period") or "",x.get("source_id") or "",x.get("id") or ""))
        promoted["record_count"] = len(promoted["data"])
        promoted["generated_at"] = now.isoformat()
        promoted["build_id"] = "source-verified-history-" + now.strftime("%Y%m%dT%H%M%SZ")
        dump(PRODUCTION, promoted)
        report["production_written"] = True
        report["new_total"] = len(promoted["data"])
    dump(REPORT, report)
    print(json.dumps({
        k: report[k] for k in ("mode","source_checked","eligible","unchanged","blocked","production_written")
    }, ensure_ascii=False))
    if conflicts:
        raise SystemExit("STOP: source-evidence / production-key gate rejected staged records")


if __name__ == "__main__":
    main()
