"""Phase 4I.7: source-isolated, dated unit-offer coverage across the Market registry.

This is a monitoring snapshot, not project ASP, sale-volume, or a new price feed.
Read *only* source-produced proof, verified offer datasets, and project metadata.
No network access and no crawler capture date substituted for listing dates.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "data/mock/market/projects.json"
MUABAN_TARGETS = ROOT / "config/market-muaban-listing-targets.json"
REVER_TARGETS = ROOT / "config/market-rever-listing-targets.json"
MUABAN_HEALTH = ROOT / "data/state/market-muaban-source-health.json"
REVER_HEALTH = ROOT / "data/state/market-rever-source-health.json"
MUABAN_OFFERS = ROOT / "data/mock/market/verified-muaban-unit-listings.json"
REVER_OFFERS = ROOT / "data/mock/market/verified-unit-listings.json"
OUT = ROOT / "data/state/market-active-listing-coverage.json"

MAX_REVER_AGE_DAYS = 90
MAX_HEALTH_AGE_HOURS = 48


def load(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def publisher_date(value):
    try:
        if not isinstance(value, str) or len(value) != 10:
            return None
        day = date.fromisoformat(value)
        return day if day.isoformat() == value else None
    except ValueError:
        return None


def recent_date(value, now, days=90):
    dt = publisher_date(value)
    return dt is not None and 0 <= (now.date() - dt).days <= days


def is_current_offer(row, now):
    if not isinstance(row, dict):
        return False
    if row.get("review_status") != "automated-two-hosted-checks":
        return False
    if row.get("asset_type") != "apartment" or row.get("metric_type") != "single-listing-asking-price-per-sqm":
        return False
    runs = row.get("verification_run_ids", [])
    if len(set(str(x) for x in runs)) < 2:
        return False
    if row.get("source_id") == "rever-vn":
        return recent_date(row.get("source_updated_date"), now, MAX_REVER_AGE_DAYS)
    if row.get("source_id") == "muaban-vn":
        start = publisher_date(row.get("source_listed_date"))
        expiry = publisher_date(row.get("source_expiration_date"))
        return bool(start and expiry and start <= now.date() <= expiry
                    and recent_date(row.get("source_listed_date"), now))
    return False


def health_is_recent(data, now):
    raw = data.get("generated_at")
    try:
        stamp = datetime.fromisoformat(raw) if raw else None
        if not stamp or not stamp.tzinfo:
            return False
        return timedelta(0) <= (now - stamp) <= timedelta(hours=MAX_HEALTH_AGE_HOURS)
    except (ValueError, TypeError):
        return False


def build(projects, muaban_targets, rever_targets, muaban_health, rever_health,
          muaban_offers, rever_offers, now):
    registry = [r for r in projects.get("data", []) if r.get("id")]
    targets = {
        "muaban-vn": {r["project_id"] for r in muaban_targets.get("targets", [])
                      if r.get("project_id")},
        "rever-vn": {r["project_id"] for r in rever_targets.get("targets", [])
                     if r.get("project_id")},
    }
    scans = {
        "muaban-vn": {r["project_id"]: r for r in muaban_health.get("sources", [])
                      if r.get("project_id")},
        "rever-vn": {r["project_id"]: r for r in rever_health.get("projects", [])
                     if r.get("project_id")},
    }
    health = {"muaban-vn": muaban_health, "rever-vn": rever_health}
    offers = [*muaban_offers.get("data", []), *rever_offers.get("data", [])]
    published = {}
    for row in offers:
        if not is_current_offer(row, now):
            continue
        if not row.get("listing_id") or not row.get("project_id"):
            continue
        key = (row["source_id"], str(row["listing_id"]))
        published[key] = row

    rows = []
    for project in registry:
        pid = project["id"]
        sources = []
        for source in ("muaban-vn", "rever-vn"):
            if pid not in targets[source]:
                continue
            status = scans[source].get(pid)
            fresh_report = health_is_recent(health[source], now)
            if source == "muaban-vn":
                candidate_count = int(status.get("qualified", 0)) if status and fresh_report else None
                accessed = status.get("access") if status and fresh_report else "not-measured-recently"
                found = status.get("discovered") if status and fresh_report else None
            else:
                candidate_count = int(status.get("recent_90_days", 0)) if status and fresh_report else None
                catalogs = status.get("catalogs", []) if status and fresh_report else []
                accessed = (
                    "reachable" if any(c.get("access_status") == "reachable" for c in catalogs)
                    else "not-measured-recently" if not catalogs
                    else "unavailable"
                )
                found = sum(int(c.get("links_discovered") or 0) for c in catalogs) if catalogs else None
            sources.append({
                "source_id": source,
                "access_status": accessed,
                "source_health_recent": bool(fresh_report and status),
                "recent_eligible_ads": candidate_count,
                "discovered_links": found,
                "last_checked_at": health[source].get("generated_at") if status else None,
            })
        project_offers = [r for r in published.values() if r["project_id"] == pid]
        project_offers.sort(key=lambda r: (r.get("source_updated_date") or "",
                                           r.get("listing_id") or ""), reverse=True)
        eligible_total = sum((x["recent_eligible_ads"] or 0) for x in sources)
        status = (
            "published-current-unit-offer" if project_offers
            else "source-qualified-awaiting-verification" if eligible_total
            else "monitored-no-current-verified-offer" if sources
            else "no-verified-unit-source-target"
        )
        rows.append({
            "project_id": pid, "project_name": project.get("name") or pid,
            "status": status, "sources_monitored": len(sources),
            "sources": sources, "recent_eligible_ads": eligible_total,
            "current_verified_ads": len(project_offers),
            "published_source_ids": sorted({r["source_id"] for r in project_offers}),
            "latest_source_listed_or_updated": max(
                (r.get("source_listed_date") or r.get("source_updated_date") or ""
                 for r in project_offers), default=None) or None,
        })
    order = {
        "no-verified-unit-source-target": 0,
        "monitored-no-current-verified-offer": 1,
        "source-qualified-awaiting-verification": 2,
        "published-current-unit-offer": 3,
    }
    rows.sort(key=lambda r: (order[r["status"]], r["project_name"].casefold()))
    return {
        "schema_version": 1, "generated_at": now.isoformat(),
        "scope": "individual-verified-apartment-asking-only",
        "project_registry_count": len(rows),
        "projects_monitored": sum(x["sources_monitored"] > 0 for x in rows),
        "projects_with_current_verified_unit_offers": sum(x["current_verified_ads"] > 0 for x in rows),
        "projects_with_recent_unpublished_source_candidates": sum(
            x["status"] == "source-qualified-awaiting-verification" for x in rows),
        "current_verified_unit_ads": sum(x["current_verified_ads"] for x in rows),
        "source_data_health": [{
            "source_id": source, "report_available": bool(health[source].get("generated_at")),
            "report_fresh": health_is_recent(health[source], now),
            "checked_at": health[source].get("generated_at"),
        } for source in ("muaban-vn", "rever-vn")],
        "projects": rows,
        "methodology": (
            "Project monitoring coverage, qualifying source candidates and fully verified current "
            "individual apartment asking listings are distinct. Verified means two distinct "
            "hosted checks; Muaban also requires unexpired source end date; Rever requires "
            "publisher update within 90 days. Project ASP, market absorption, representative "
            "price range and actual transaction value are not computed."
        ),
    }


def main():
    now = datetime.now(timezone.utc)
    result = build(
        load(PROJECTS, {"data": []}),
        load(MUABAN_TARGETS, {"targets": []}),
        load(REVER_TARGETS, {"targets": []}),
        load(MUABAN_HEALTH, {}), load(REVER_HEALTH, {}),
        load(MUABAN_OFFERS, {"data": []}), load(REVER_OFFERS, {"data": []}), now,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("projects", "methodology")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
