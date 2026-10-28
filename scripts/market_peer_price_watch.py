#!/usr/bin/env python3
"""Monitor publisher access and *age* of reviewed peer price evidence.

Checks never promote price candidates or overwrite source-reviewed price ranges.
A successful HTTP check is NOT a successful price update, and blocked portals are
reported honestly without trying to bypass access controls.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/mock/market/listing-scope-evidence.json"
PROJECTS = ROOT / "data/mock/market/projects.json"
OUT = ROOT / "data/state/market-peer-price-watch.json"
TARGETS = ("aqua-city", "springville", "elyse-island", "kita-airport-city", "izumi-city")
ALLOWED_HOST = "batdongsan.com.vn"
HEADERS = {
    "User-Agent": "RealEstateMarketIntelligence/1.0 (source availability monitoring; no data extraction)"
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def days_since(day: str | None, today: date) -> int | None:
    if not day:
        return None
    return (today - date.fromisoformat(day)).days


def access(url: str, fetcher=None) -> dict:
    u = urlparse(url)
    if u.scheme != "https" or u.hostname not in (ALLOWED_HOST, "www." + ALLOWED_HOST):
        return {"state": "invalid-source-url", "http_status": None}
    try:
        response = fetcher(url) if fetcher else requests.get(
            url, headers=HEADERS, timeout=12, allow_redirects=True
        )
        final = urlparse(getattr(response, "url", url))
        # A redirect to an unrelated domain is NOT verification of the source.
        if final.scheme != "https" or final.hostname not in (ALLOWED_HOST, "www." + ALLOWED_HOST):
            return {"state": "unexpected-redirect", "http_status": response.status_code}
        status = response.status_code
        if status == 200:
            state = "reachable-unverified-price"
        elif status in (401, 403, 429):
            state = "blocked"
        else:
            state = "http-error"
        return {"state": state, "http_status": status}
    except requests.RequestException:
        return {"state": "unavailable", "http_status": None}


def build(*, today: date | None = None, fetcher=None):
    today = today or datetime.now(timezone.utc).date()
    evidence = load(EVIDENCE)["data"]
    projects = {x["id"]: x for x in load(PROJECTS)["data"]}
    rows = []
    for pid in TARGETS:
        if pid not in projects:
            raise ValueError(f"Missing tracked project: {pid}")
        scoped = [x for x in evidence if x.get("project_id") == pid]
        scoped.sort(key=lambda x: (x.get("review_date") or "", x.get("id") or ""), reverse=True)
        current = next((x for x in scoped if x.get("coverage_status") !=
                        "historical-segment-reference-not-current"), None)
        last = current or (scoped[0] if scoped else None)
        if not last:
            rows.append({"project_id": pid, "project_name": projects[pid]["name"],
                         "price_evidence": "missing", "publisher_access": "not-configured",
                         "last_review_date": None, "source_listing_age_days": None})
            continue
        age = days_since(last.get("latest_listing_date"), today)
        historical = current is None
        caution = "historic-only" if historical else (
            "source-activity-old" if age is None or age > 30 else "source-activity-recent"
        )
        state = access(last["source_url"], fetcher=fetcher)
        rows.append({
            "project_id": pid, "project_name": projects[pid]["name"],
            "source_id": last["source_id"], "source_url": last["source_url"],
            "source_product_scope": last["price_scope"],
            "price_evidence": "historical-only" if historical else "reviewed-scope-only",
            "price_caution": caution,
            "last_review_date": last.get("review_date"),
            "last_publisher_listing_date": last.get("latest_listing_date"),
            "source_listing_age_days": age,
            "publisher_access": state["state"], "http_status": state["http_status"],
            "data_published_from_this_check": False
        })
    counts = {
        "targets": len(rows),
        "scoped_current_review_records": sum(x["price_evidence"] == "reviewed-scope-only" for x in rows),
        "historical_only": sum(x["price_evidence"] == "historical-only" for x in rows),
        "missing_prices": sum(x["price_evidence"] == "missing" for x in rows),
        "blocked_sources": sum(x["publisher_access"] == "blocked" for x in rows),
        "old_publisher_activity": sum(x.get("price_caution") == "source-activity-old" for x in rows)
    }
    return {
        "schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of_date": today.isoformat(), "monitor_type": "source-access-and-evidence-age-only",
        "source_verified_new_prices": 0, "production_prices_written": False,
        "counts": counts, "projects": rows,
        "policy": "HTTP success proves accessibility only. Reviewed price rows remain unchanged until separately verified against the correct product category and source date. Never fabricate trend points."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUT))
    args = parser.parse_args()
    result = build()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "written", "counts": result["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
