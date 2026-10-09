"""Rever public project-sale listing scanner (source-isolated, fail-closed).

The project catalog discovers current listing URLs dynamically; each listing must
independently confirm its own project, apartment product type, dated update,
advertised total price, unit rate and area. Portal counts, category ranges,
sales volumes and average project ASP are never inferred.

Only identical detail-page evidence on two distinct scheduled GitHub runs
>= 60 minutes apart can release a recently updated individual listing. Older
listings stay diagnostics only, not artificially re-dated by crawler captures.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/market-rever-listing-targets.json"
STATE = ROOT / "data/state/market-rever-listing-verification.json"
OUTPUT = ROOT / "data/mock/market/verified-unit-listings.json"
REPORT = ROOT / "data/candidate/market/market-rever-listing-report.json"
HOST = "rever.vn"
CAP = 3_000_000
MAX_LISTINGS_PER_PROJECT = 12
MAX_AGE_DAYS = 90
MAX_CHECKS = 8
AGENT = "MarketIntelligenceResearchBot/1.0 (public market evidence monitoring)"

ID = re.compile(r"\b(?:ATA|A\d{2}|T\d{2})\d{4,9}\b", re.I)
DATE = re.compile(r"Cập nhật\s*:\s*(\d{2})/(\d{2})/(20\d{2})", re.I)
PRICE = re.compile(r"(\d+(?:[.,]\d+)?)\s*tỷ\s+(\d+(?:[.,]\d+)?)\s*triệu\s*/\s*m[²2]", re.I)
AREA = re.compile(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*m[²2]\b", re.I)
PROJECT = re.compile(r"\bDự án\s*:?\s*([^\n]{3,80}?)(?=\s+Giá bán|\s+Tiện ích|\s+Xem chi tiết|$)", re.I)
BANNED = re.compile(r"cho thuê|phòng trọ|office.?tel|nhà phố|biệt thự|shophouse|đất nền", re.I)


def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_url(url, listing=False):
    u = urlsplit(url)
    if u.scheme != "https" or u.hostname != HOST or u.username or u.password or u.query or u.fragment:
        return None
    if listing and (not u.path.startswith("/mua/") or len(u.path) < 8):
        return None
    if not listing and not u.path.startswith("/s/"):
        return None
    return f"https://{HOST}{u.path.rstrip('/')}"


def discover(html, index_url):
    if not safe_url(index_url):
        return []
    soup = BeautifulSoup(html, "lxml")
    found = []
    for link in soup.select("a[href]"):
        url = safe_url(urljoin(index_url, link.get("href", "")), listing=True)
        if url and url not in found:
            found.append(url)
    return found[:MAX_LISTINGS_PER_PROJECT]


def money(raw):
    return float(raw.replace(",", "."))


def parse_detail(html, url, expected_name, project_id, captured):
    if not safe_url(url, listing=True):
        return None, "invalid-url"
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    heading = soup.find("h1")
    if not heading:
        return None, "missing-listing-header"
    title = " ".join(heading.get_text(" ", strip=True).split())
    if BANNED.search(title):
        return None, "wrong-product-type"
    raw = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", raw)
    # Strong project attribution: explicit project field on property detail,
    # not a neighborhood recommendation mentioning the desired project.
    match_project = re.search(
        r"(?:Dự án|Project)\s*:?\s*([\wÀ-ỹ\s\-]{3,90})(?=\s+Giá bán|\s+Tình trạng|\s+Tìm kiếm|\s+Xem chi tiết)",
        text, re.I
    )
    match_title = re.search(re.escape(expected_name), title, re.I)
    if not match_project or " ".join(match_project.group(1).casefold().split()) != expected_name.casefold():
        return None, "project-not-explicit"
    if not match_title and expected_name.casefold() not in text[:800].casefold():
        return None, "listing-heading-not-project-scoped"
    # Evaluate listing price in the compact summary before full-description
    # suggested listings, avoiding unrelated price amounts.
    h_end = text.find(title)
    header = text[h_end:h_end + 650] if h_end >= 0 else ""
    ident = ID.search(header)
    dt = DATE.search(header)
    price = PRICE.search(header)
    area = AREA.search(header)
    if not (ident and dt and price and area):
        return None, "incomplete-unit-price-date-evidence"
    try:
        updated = date(int(dt.group(3)), int(dt.group(2)), int(dt.group(1)))
    except ValueError:
        return None, "invalid-source-date"
    if updated > captured.date():
        return None, "publisher-future-date"
    vnd = round(money(price.group(1)) * 1_000_000_000)
    per_sqm = round(money(price.group(2)) * 1_000_000)
    sqm = money(area.group(1))
    if not (0.4e9 <= vnd <= 250e9 and 30 <= sqm <= 450
            and 5e6 <= per_sqm <= 700e6):
        return None, "implausible-price-or-area"
    if abs(vnd / sqm - per_sqm) / per_sqm > .03:
        return None, "inconsistent-price-per-sqm-and-area"
    return {
        "project_id": project_id, "project_name": expected_name,
        "source_id": "rever-vn", "source_url": url,
        "listing_id": ident.group(0).upper(),
        "listing_title": title[:160], "asset_type": "apartment",
        "market_layer": "individual-listing-asking",
        "metric_type": "single-listing-asking-price-per-sqm",
        "source_updated_date": updated.isoformat(),
        "listed_area_sqm": sqm, "listing_price_vnd": vnd,
        "value_vnd_per_m2": per_sqm,
        "publication_status": "candidate-source-evidence",
        "source_publication_date": None,
        "methodology_note": "One Rever apartment advertisement only, not the project median, transaction price or ASP. Publisher listing update date is not an aggregation date.",
    }, "parsed-listing"


def fetch(session, url, listing=False):
    if not safe_url(url, listing=listing):
        return None, "unsafe-url"
    try:
        res = session.get(url, timeout=18, stream=True, headers={
            "User-Agent": AGENT, "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept": "text/html,application/xhtml+xml"}, allow_redirects=True)
        if not safe_url(res.url, listing=listing):
            res.close()
            return None, "off-host-redirect"
        if res.status_code in (401, 403, 429):
            res.close()
            return None, "access-blocked"
        if res.status_code != 200 or "html" not in res.headers.get("Content-Type", "").lower():
            res.close()
            return None, "http-error-or-non-html"
        chunks = []
        total = 0
        for chunk in res.iter_content(32768):
            total += len(chunk)
            if total > CAP:
                res.close()
                return None, "oversized-document"
            chunks.append(chunk)
        res.close()
        return b"".join(chunks).decode(res.encoding or "utf-8", "replace"), "reachable"
    except requests.RequestException:
        return None, "network-error"


def signature(row):
    payload = [row[k] for k in ("project_id", "listing_id", "source_url",
        "source_updated_date", "listing_price_vnd", "value_vnd_per_m2", "listed_area_sqm")]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def evaluate(previous, rows, seen, now, run_id):
    """Persistent verification state and immutable publisher-dated listing releases."""
    identities = {r["listing_id"]: r for r in rows}
    states = {r["listing_id"]: r for r in previous.get("listings", [])}
    accepted = []
    decisions = []
    for detail in seen:
        lid = detail["listing_id"]
        fingerprint = signature(detail)
        existing = states.get(lid, {})
        checks = existing.get("checks", [])
        check = {"run_id": str(run_id), "checked_at": now.isoformat(),
                 "signature": fingerprint, "source_updated_date": detail["source_updated_date"]}
        if not any(r["run_id"] == str(run_id) for r in checks):
            checks = (checks + [check])[-MAX_CHECKS:]
        states[lid] = {"listing_id": lid, "project_id": detail["project_id"],
                       "source_url": detail["source_url"], "checks": checks}
        decision = "waiting-for-independent-verification"
        if lid in identities:
            decision = "previously-recorded"
        elif (now.date() - date.fromisoformat(detail["source_updated_date"])).days > MAX_AGE_DAYS:
            decision = "historical-listing-not-current"
        elif len(checks) >= 2 and checks[-1]["signature"] == checks[-2]["signature"] and (
                checks[-1]["run_id"] != checks[-2]["run_id"]):
            try:
                a, b = (datetime.fromisoformat(x["checked_at"]) for x in checks[-2:])
                if a.tzinfo and b.tzinfo and b-a >= timedelta(hours=1):
                    accepted.append({**detail,
                        "id": "rever-" + detail["listing_id"].lower() + "-" + fingerprint[:12],
                        "review_status": "automated-two-hosted-checks",
                        "verification_run_ids": [x["run_id"] for x in checks[-2:]],
                        "verified_at": now.isoformat()})
                    decision = "independent-live-listing-verified"
                else:
                    decision = "checks-under-one-hour"
            except (ValueError, KeyError, TypeError):
                decision = "invalid-source-proof"
        decisions.append({"listing_id": lid, "project_id": detail["project_id"],
                          "source_updated_date": detail["source_updated_date"],
                          "decision": decision})
    return {"schema_version": 1, "listings": sorted(states.values(), key=lambda x:x["listing_id"])}, accepted, decisions


def run(config, history, state, fetcher, now, run_id):
    discovered, qualifying = 0, []
    diagnostics = []
    inspected = set()
    for target in config["targets"]:
        html, access = fetcher(target["url"], listing=False)
        urls = discover(html, target["url"]) if html else []
        checks = {"project_id":target["project_id"], "source_url":target["url"],
                  "index_status":access, "listing_links":len(urls),
                  "details_checked":0, "qualified":0, "reasons":{}}
        for url in urls:
            if url in inspected:
                continue
            inspected.add(url)
            body, status = fetcher(url, listing=True)
            checks["details_checked"] += 1
            if body is None:
                reason = status
                row = None
            else:
                row, reason = parse_detail(body, url, target["publisher_project_name"],
                                           target["project_id"], now)
            checks["reasons"][reason] = checks["reasons"].get(reason, 0) + 1
            if row:
                checks["qualified"] += 1
                qualifying.append(row)
        discovered += len(urls)
        diagnostics.append(checks)
    updated, additions, decisions = evaluate(state, history.get("data", []), qualifying, now, run_id)
    production = {
        **history, "schema_version": 1,
        "collection_mode": "individually-publisher-verified-apartment-asking-only",
        "record_count": len(history.get("data", [])) + len(additions),
        "data": (history.get("data", []) + additions)[-250:],
    }
    report = {"schema_version":1, "generated_at":now.isoformat(),
              "targets_checked":len(config["targets"]),
              "listing_urls_discovered":discovered, "qualified_current_or_historical":len(qualifying),
              "accepted_new_individual_listings":len(additions),
              "production_project_aggregates_changed":False,
              "sources":diagnostics, "decisions":decisions}
    return production, updated, report


def main():
    config = load(CONFIG, {"targets":[]})
    history = load(OUTPUT, {"data":[]})
    previous = load(STATE, {})
    session = requests.Session()
    now = datetime.now(timezone.utc)
    run_id = os.environ.get("GITHUB_RUN_ID", now.isoformat())
    prod, state, report = run(config, history, previous,
        lambda url, listing: fetch(session,url,listing), now, run_id)
    save(OUTPUT, prod)
    save(STATE, state)
    save(REPORT, report)
    print(json.dumps({k:v for k,v in report.items() if k!="decisions"},ensure_ascii=False))


if __name__ == "__main__":
    main()
