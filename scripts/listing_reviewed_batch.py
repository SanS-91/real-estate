"""Curated assisted listing snapshots, with literal metric evidence and no invented dates.

This path is for exact project-page data reviewed from search-indexed public pages.
It does not pretend GitHub Actions has successfully fetched a blocked portal.
Every new point is dated when reviewed and retains the source's last-listing
timestamp separately; the latter is NOT the aggregate price reporting date.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/listing-reviewed-captures-20261009.json"
PRODUCTION = ROOT / "data/mock/market/listing-observations.json"
CANDIDATE = ROOT / "data/candidate/market/listing-observations.json"
REPORT = ROOT / "data/candidate/market/listing-reviewed-batch-report.json"
PROJECTS = ROOT / "data/mock/market/projects.json"

FIELDS = (
    "asking_price_low_vnd_per_m2", "asking_price_high_vnd_per_m2",
    "asking_price_change_1y_pct", "popular_area_low_sqm", "popular_area_high_sqm",
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def number_vi(raw):
    text = str(raw).strip()
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    return float(text)


def quote_range(text):
    match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*(?:tr(?:iệu)?)(?:/|\s*/\s*)m(?:²|2)",
        text or "", re.I,
    )
    return (int(round(number_vi(match.group(1)) * 1_000_000)),
            int(round(number_vi(match.group(2)) * 1_000_000))) if match else None


def quote_trend(text):
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*%\s*Giá bán đã\s*(tăng|giảm)", text or "", re.I)
    if not match:
        return None
    value = number_vi(match.group(1)) / 100
    return round(value if match.group(2).lower() == "tăng" else -value, 6)


def quote_area(text):
    match = re.search(r"Diện tích phổ biến\s*\|?\s*(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*m(?:²|2)", text or "", re.I)
    return (number_vi(match.group(1)), number_vi(match.group(2))) if match else None


def quote_listing_count(text):
    match = re.search(r"Số lượng\s*\|?\s*(\d[\d.,]*)\s*căn", text or "", re.I)
    if not match:
        return None
    return int(re.sub(r"\D", "", match.group(1)))


def quote_as_of(text):
    match = re.search(r"Cập nhật tin đăng gần đây nhất\s*\|?\s*(\d{2})-(\d{2})-(\d{4})", text or "", re.I)
    if not match:
        return None
    try:
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1))).isoformat()
    except ValueError:
        return None


def source_url_matches(target, baseline):
    source = urlsplit(target)
    prior = urlsplit(baseline)
    allowed = {"batdongsan.com.vn", "www.batdongsan.com.vn"}
    return (
        source.scheme == prior.scheme == "https"
        and source.hostname in allowed
        and source.hostname == prior.hostname
        and source.path.rstrip("/") == prior.path.rstrip("/")
        and not source.query and not source.fragment
    )


def validate_capture(item, prior, today):
    problems = []
    if not prior or not source_url_matches(item.get("source_url", ""), prior.get("source_url", "")):
        problems.append("source-link-does-not-match-project-mapping")
    if not prior or item.get("asset_type") != prior.get("asset_type"):
        problems.append("unsupported-or-changed-asset-type")
    try:
        reviewed = date.fromisoformat(item.get("observation_date") or "")
        last_listing = date.fromisoformat(item.get("source_data_as_of") or "")
        if reviewed > today:
            problems.append("future-review-date")
        if last_listing > reviewed:
            problems.append("last-listing-date-after-review-date")
        if (reviewed - last_listing).days > 21:
            problems.append("stale-last-listing-date")
        if prior and reviewed <= date.fromisoformat(prior.get("observation_date") or ""):
            problems.append("not-a-new-snapshot-date")
    except ValueError:
        problems.append("invalid-snapshot-or-source-date")

    evidence = item.get("evidence") or {}
    low, high = item.get("asking_price_low_vnd_per_m2"), item.get("asking_price_high_vnd_per_m2")
    if (low is None or high is None or low <= 0 or high <= low or high > 1_000_000_000):
        problems.append("invalid-positive-asking-price-range")
    if quote_range(evidence.get("price")) != (low, high):
        problems.append("price-range-does-not-match-source-text")
    if quote_trend(evidence.get("trend")) != item.get("asking_price_change_1y_pct"):
        problems.append("1y-price-trend-does-not-match-source-text")
    area = quote_area(evidence.get("area"))
    if (item.get("popular_area_low_sqm"), item.get("popular_area_high_sqm")) == (None, None):
        if evidence.get("area"):
            problems.append("unrecorded-source-area-evidence")
    elif not area or area != (item.get("popular_area_low_sqm"), item.get("popular_area_high_sqm")):
        problems.append("popular-area-does-not-match-source-text")
    if quote_listing_count(evidence.get("listing_count")) != item.get("listing_count"):
        problems.append("listing-count-does-not-match-source-text")
    if quote_as_of(evidence.get("last_listing")) != item.get("source_data_as_of"):
        problems.append("last-listing-date-does-not-match-source-text")
    if prior:
        signature = lambda row: tuple(row.get(f) for f in FIELDS)
        if signature(prior) == signature(item):
            problems.append("unchanged-primary-metrics-not-an-independent-observation")
    return problems


def make_candidate(item, prior):
    result = copy.deepcopy(prior)
    pid = item["project_id"]
    obs_date = item["observation_date"]
    result.update({
        "id": f"bdsc-{pid}-{obs_date}",
        "source_url": item["source_url"],
        "observation_date": obs_date,
        "source_data_as_of": item["source_data_as_of"],
        "market_layer": "listing-asking",
        "coverage_status": "full",
        "status": "reviewed",
        "confidence": "reviewed-public-index-snapshot",
        "product_price_ranges": [],
        "methodology_note": (
            "Manually reviewed public publisher project-page aggregate asking range, captured from a fresh "
            "search-indexed excerpt. Source's 'latest listing updated' date is NOT the timestamp for computing "
            "this aggregate range. Listing-year percentage is publisher-reported, NOT change between local snapshots. "
            "No sales/transaction price inference. Listing counts are ancillary."
        ),
        "volatile_metrics": {
            "listing_count": item["listing_count"],
            "project_views_7d": None,
            "use_in_primary_kpi": False,
            "note": "Counts belong to the publisher's search page and can change intraday; not used in price KPI.",
        },
        "provenance": {
            "capture_mode": "assisted-reviewed-public-index",
            "source_review_date": obs_date,
            "last_listing_date": item["source_data_as_of"],
            "last_listing_date_is_price_timestamp": False,
            "source_evidence": copy.deepcopy(item["evidence"]),
            "source_access": "public-index-only-github-runner-blocked",
            "verified_fields": ["asking_price_range", "publisher_1y_trend", "latest_listing_date"],
            "review_required": False,
        },
    })
    for field in FIELDS:
        result[field] = item[field]
    return result


def evaluate(captures, production, today):
    existing = {}
    for row in sorted(production, key=lambda x: (x.get("project_id") or "", x.get("observation_date") or "")):
        existing[row["project_id"]] = row
    decisions, rows, seen = [], [], set()
    by_day = {(r.get("project_id"), r.get("observation_date")): r for r in production}
    for item in captures:
        pid = item.get("project_id")
        prior = existing.get(pid)
        if pid in seen:
            decisions.append({"project_id": pid, "status": "manual-review-required",
                              "reasons": ["duplicate-project-in-capture-batch"]})
            continue
        seen.add(pid)
        archived = by_day.get((pid, item.get("observation_date")))
        if archived:
            # Idempotent reruns of scheduled/reviewed workflows must never add
            # repeated daily records or silently change previously published data.
            matches = (all(archived.get(field) == item.get(field) for field in FIELDS)
                       and archived.get("source_url") == item.get("source_url")
                       and archived.get("source_data_as_of") == item.get("source_data_as_of")
                       and (archived.get("volatile_metrics") or {}).get("listing_count") == item.get("listing_count")
                       and (archived.get("provenance") or {}).get("source_evidence") == item.get("evidence"))
            decisions.append({"project_id": pid,
                              "status": "unchanged" if matches else "manual-review-required",
                              "reasons": [] if matches else ["conflict-with-same-day-observation"]})
            continue
        problems = validate_capture(item, prior, today)
        if problems:
            decisions.append({"project_id": pid, "status": "manual-review-required", "reasons": problems})
        else:
            rows.append(make_candidate(item, prior))
            decisions.append({"project_id": pid, "status": "ready", "date": item["observation_date"]})
    return rows, decisions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", default=None, help="Override clock for reproducible tests, YYYY-MM-DD")
    parser.add_argument("--config", default=str(CONFIG), help="Reviewed publisher-evidence batch JSON")
    args = parser.parse_args()
    today = date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()
    cfg = read(Path(args.config))
    production = read(PRODUCTION)
    expected_projects = {p["id"] for p in read(PROJECTS)["data"]}
    captures = cfg["records"]
    ready, decisions = evaluate(captures, production.get("data", []), today)
    errors = [d for d in decisions if d["status"] not in ("ready", "unchanged")]
    errors += [{"project_id": d.get("project_id"), "reasons": ["project-not-in-project-registry"]}
               for d in captures if d.get("project_id") not in expected_projects]
    timestamp = datetime.now(timezone.utc).isoformat()
    report = {
        "schema_version": 1, "generated_at": timestamp,
        "sources_checked": len(captures), "ready": len(ready),
        "unchanged": sum(d["status"] == "unchanged" for d in decisions),
        "blocked": len(errors), "production_written": False,
        "source_access": "assisted-reviewed-index",
        "source_data_not_directly_refetched_on_github": True,
        "decisions": decisions,
    }
    save(CANDIDATE, {"schema_version": 1, "candidate_only": True, "generated_at": timestamp,
                     "observation_date": cfg.get("captured_on"), "record_count": len(ready), "data": ready})
    save(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("Reviewed listing batch blocked: source evidence, dating, or project mapping mismatch.")


if __name__ == "__main__":
    main()
