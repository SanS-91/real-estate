#!/usr/bin/env python3
"""Build a source-dated market news/project index and honest coverage health.

No scraping, price estimation, status inference or synthetic observations.
The published article registry is the only source for article links.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "data/mock/market/projects.json"
ARTICLES = ROOT / "data/mock/articles/articles.json"
OBSERVATIONS = ROOT / "data/mock/market/observations.json"
LISTINGS = ROOT / "data/mock/market/listing-observations.json"
ACTIVE_COVERAGE = ROOT / "data/state/market-active-listing-coverage.json"
SOURCE_COVERAGE = ROOT / "data/state/listing-source-coverage.json"
RESEARCH_BRIEFS = ROOT / "data/mock/market/research-briefs.json"
OUTPUT = ROOT / "data/processed/market/market-daily-pulse.json"


def read_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def fold(value: str) -> str:
    value = unicodedata.normalize("NFD", str(value or "").lower().replace("đ", "d"))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def matches(text: str, phrase: str) -> bool:
    return bool(phrase) and (" " + fold(phrase) + " ") in (" " + fold(text) + " ")


def parse_instant(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result.astimezone(timezone.utc)
    except ValueError:
        return None


def valid_article(row, now):
    if not isinstance(row, dict):
        return False
    url = str(row.get("url") or "")
    u = urlparse(url)
    if u.scheme != "https" or not u.netloc or not str(row.get("title") or "").strip():
        return False
    if str(row.get("source_id") or "").startswith("demo-"):
        return False
    when = parse_instant(row.get("published_at"))
    return when is not None and when <= now + timedelta(hours=1) and when >= now - timedelta(days=30)


def project_phrases(project):
    name = project.get("name", "")
    phrases = [name]
    if "(" in name and ")" in name:
        phrases.append(name.split("(", 1)[0].strip())
        phrases.append(name.split("(", 1)[1].split(")", 1)[0].strip())
    # Do not use generic developer/area words to infer a project.
    return [p for p in phrases if len(fold(p).replace(" ", "")) >= 6]


def source_latest_date(rows, field):
    return max((str(row.get(field)) for row in rows if row.get(field)), default=None)


def age_days(value, now):
    if not value:
        return None
    date = str(value)[:10]
    try:
        return max(0, (now.date() - datetime.strptime(date, "%Y-%m-%d").date()).days)
    except ValueError:
        return None


def build(projects, articles, observations, listings, active, source, now=None, research_briefs=None):
    now = now or datetime.now(timezone.utc)
    project_by_id = {p["id"]: p for p in projects if p.get("id") and p.get("name")}
    indexed = defaultdict(list)
    accepted = 0
    inferred = 0
    for row in articles:
        if not valid_article(row, now):
            continue
        accepted += 1
        explicit = {pid for pid in (row.get("project_ids") or []) if pid in project_by_id}
        title = row["title"]
        inferred_ids = {
            pid for pid, project in project_by_id.items()
            if any(matches(title, phrase) for phrase in project_phrases(project))
        }
        for project_id in sorted(explicit | inferred_ids):
            method = "source-project-id" if project_id in explicit else "exact-headline-name"
            if method == "exact-headline-name":
                inferred += 1
            indexed[project_id].append({
                "project_id": project_id,
                "article_id": row.get("id"),
                "title": title,
                "url": row["url"],
                "source_id": row.get("source_id"),
                "published_at": row["published_at"],
                "match_method": method,
                "category": row.get("category"),
            })

    by_project = []
    news = []
    for pid, project in project_by_id.items():
        rows = sorted(indexed[pid], key=lambda x: (x["published_at"], x["url"]), reverse=True)
        seen = set()
        unique = []
        for row in rows:
            if row["url"] not in seen:
                seen.add(row["url"])
                unique.append(row)
        last7 = sum(parse_instant(row["published_at"]) >= now - timedelta(days=7) for row in unique)
        by_project.append({
            "project_id": pid,
            "project_name": project["name"],
            "region_ids": project.get("region_ids", []),
            "matched_articles_30d": len(unique),
            "matched_articles_7d": last7,
            "last_article_at": unique[0]["published_at"] if unique else None,
        })
        news.extend(unique[:3])

    news.sort(key=lambda x: (x["published_at"], x["project_id"]), reverse=True)
    listings_valid = [r for r in listings if r.get("observation_date") and
        r.get("asking_price_low_vnd_per_m2") is not None and
        r.get("asking_price_high_vnd_per_m2") is not None]
    latest_listing = source_latest_date(listings_valid, "observation_date")
    latest_research = source_latest_date(observations, "source_date")
    price_age = age_days(latest_listing, now)
    research_age = age_days(latest_research, now)
    latest_metric_quarter = max(
        (row.get("period") for row in observations
         if row.get("scope_type") == "region-segment"
         and row.get("period_type") == "quarter"
         and isinstance(row.get("period"), str)
         and re.fullmatch(r"20\d{2}-Q[1-4]", row["period"])),
        default=None)
    latest_published_quarter = max(
        (row.get("period") for row in (research_briefs or [])
         if row.get("period_type") == "quarter"
         and row.get("data_basis") == "qualitative-publisher-report"
         and isinstance(row.get("period"), str)
         and re.fullmatch(r"20\d{2}-Q[1-4]", row["period"])
         and age_days(row.get("source_date"), now) is not None),
        default=None)
    newer_report_pending_metrics = bool(
        latest_published_quarter and (not latest_metric_quarter or
        latest_published_quarter > latest_metric_quarter))
    return {
        "schema_version": 1,
        "generated_at": now.replace(microsecond=0).isoformat(),
        "description": "Derived market article-to-project index and evidence freshness; not live price or transactions.",
        "source_scope": "existing publisher articles + dated project and market JSON",
        "project_count": len(project_by_id),
        "articles_screened_30d": accepted,
        "inferred_headline_associations_30d": inferred,
        "projects_with_articles_30d": sum(x["matched_articles_30d"] > 0 for x in by_project),
        "project_updates": sorted(by_project, key=lambda x: (x["matched_articles_30d"], x["last_article_at"] or ""), reverse=True),
        "article_index": news[:80],
        "data_freshness": {
            "listing_aggregate": {
                "observation_date": latest_listing,
                "age_days": price_age,
                "stale": price_age is None or price_age > 14,
                "record_count": len(listings_valid),
                "metric_basis": "historical portal asking ranges, not transactions",
            },
            "supply_sales_research": {
                "latest_source_date": latest_research,
                "age_days": research_age,
                "stale": research_age is None or research_age > 100 or newer_report_pending_metrics,
                "latest_quantitative_quarter": latest_metric_quarter,
                "latest_published_qualitative_report_quarter": latest_published_quarter,
                "newer_research_report_pending_verified_metrics": newer_report_pending_metrics,
                "record_count": len(observations),
                "metric_basis": "publisher quarterly/annual reports, NOT daily statistics",
            },
            "unit_listing_monitor": {
                "last_checked_at": active.get("generated_at"),
                "projects_monitored": active.get("projects_monitored", 0),
                "projects_with_current_verified_offers": active.get("projects_with_current_verified_unit_offers", 0),
                "current_verified_unit_ads": active.get("current_verified_unit_ads", 0),
                "scope": "individual apartment listings only; not project average",
            },
            "listing_collector": {
                "last_checked_at": source.get("source_checked_at"),
                "access_status": source.get("source_access", "unknown"),
                "new_candidates": source.get("source_candidate_records", 0),
            },
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    inputs = [
        read_json(PROJECTS), read_json(ARTICLES),
        read_json(OBSERVATIONS), read_json(LISTINGS),
        read_json(ACTIVE_COVERAGE), read_json(SOURCE_COVERAGE),
        read_json(RESEARCH_BRIEFS)
    ]
    # Fail closed on absent/malformed inputs; never replace good data with an empty file.
    for index in range(4):
        if not isinstance(inputs[index].get("data"), list):
            raise ValueError("Required input has no data array")
    if not isinstance(inputs[6].get("data"), list):
        raise ValueError("Research-brief manifest missing data array")
    result = build(*(obj["data"] for obj in inputs[:4]), inputs[4], inputs[5],
                   research_briefs=inputs[6]["data"])
    if result["project_count"] < 1 or not result["data_freshness"]["supply_sales_research"]["record_count"]:
        raise ValueError("Registry or research data unexpectedly empty")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Market pulse: projects=%d, linked=%d, articles=%d, listing_stale=%s" % (
        result["project_count"], result["projects_with_articles_30d"],
        result["articles_screened_30d"], result["data_freshness"]["listing_aggregate"]["stale"]
    ))


if __name__ == "__main__":
    main()
