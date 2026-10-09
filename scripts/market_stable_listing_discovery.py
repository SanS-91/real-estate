"""Phase 4H: independently discover secondary *listing* price evidence.

Publisher-relative update labels are never treated as monthly source periods.
Data stays in candidate/state lanes, NEVER canonical project ASP or price charts.
No login, headless challenges, or protected endpoints are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/market-stable-listing-sources.json"
STATE = ROOT / "data/state/market-stable-listing-health.json"
QUEUE = ROOT / "data/candidate/market/stable-listing-candidates.json"
REPORT = ROOT / "data/candidate/market/stable-listing-run-report.json"
HOST = "www.nhatot.com"
MAX_BYTES = 4_000_000
HEADERS = {"User-Agent": "MarketIntelligenceResearchBot/1.0 (public listing research)",
           "Accept": "text/html,application/xhtml+xml",
           "Accept-Language": "vi-VN,vi;q=0.9"}
LISTING_PATH = re.compile(r"^/mua-ban-can-ho-chung-cu-[a-z0-9-]+/(\d{8,12})\.htm/?$")
TRIPLE = re.compile(r"(\d+(?:[.,]\d+)?)\s*tỷ\s+(\d+(?:[.,]\d+)?)\s*triệu\s*/?\s*m[²2]\s*(\d+(?:[.,]\d+)?)\s*m[²2]", re.I)
PROJECT = re.compile(r"Dự\s*Án\s*:\s*([^\n]{3,90}?)(?=\s+Nhấn để xem|\s+Cập nhật|$)", re.I)
BLOCKED = re.compile(r"captcha|just a moment|verify you are human|checking your browser|access denied", re.I)


def read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normal_url(url, listing=True):
    u = urlsplit(url)
    if u.scheme != "https" or u.hostname != HOST or u.username or u.password or u.query or u.fragment:
        return None
    if listing and not LISTING_PATH.fullmatch(u.path):
        return None
    return urlunsplit(("https", HOST, u.path.rstrip("/"), "", ""))


def discover(html, category_url, limit=18):
    """Find individual listing links dynamically, not manually pin each ad."""
    if not normal_url(category_url, listing=False):
        return []
    found = []
    for a in BeautifulSoup(html, "lxml").select("a[href]"):
        url = normal_url(urljoin(category_url, a.get("href", "")))
        if url and url not in found:
            found.append(url)
        if len(found) >= limit:
            break
    return found


def decimal(x):
    return float(x.replace(",", "."))


def parse_listing(html, url, projects):
    canonical = normal_url(url)
    if not canonical:
        return None, "untrusted-url"
    soup = BeautifulSoup(html, "lxml")
    for el in soup(["script", "style", "noscript"]):
        el.decompose()
    main = soup.find("main") or soup.body or soup
    heading = main.find("h1")
    if not heading:
        return None, "missing-listing-heading"
    name = heading.get_text(" ", strip=True)
    if re.search(r"\bcho\s*thuê\b", name, re.I):
        return None, "rental-not-sale"
    text = re.sub(r"\s+", " ", main.get_text(" ", strip=True))
    if BLOCKED.search(text[:700]):
        return None, "blocked-or-challenge"
    at = text.find(name)
    if at < 0:
        return None, "heading-not-found"
    header = text[at:at + 520]
    m = TRIPLE.search(header)
    if not m:
        return None, "no-explicit-unit-price"
    total, unit, area = (decimal(m.group(i)) for i in (1, 2, 3))
    if not (0.3 <= total <= 250 and 10 <= unit <= 1000 and 20 <= area <= 500):
        return None, "implausible-price-or-area"
    calculated = total * 1000 / area
    if abs(calculated - unit) / unit > .075:
        return None, "inconsistent-price-area-units"
    p = PROJECT.search(text[:max(1000, at + 1800)])
    if not p:
        return None, "no-explicit-project-link"
    label = " ".join(p.group(1).split())
    ids = [pid for pid, pname in projects.items() if label.casefold() == pname.casefold()]
    if len(ids) != 1:
        return None, "not-an-allowlisted-project"
    listing_id = LISTING_PATH.fullmatch(urlsplit(canonical).path).group(1)
    return {
        "listing_id": listing_id,
        "project_id": ids[0],
        "publisher_project_name": label,
        "source_id": "nhatot-vn",
        "source_url": canonical,
        "title": name[:160],
        "market_layer": "listing-asking",
        "listing_price_vnd": round(total * 1_000_000_000),
        "publisher_unit_asking_vnd_per_m2": round(unit * 1_000_000),
        "area_sqm": area,
        "source_price_period": None,
        "verification_status": "unreviewed-candidate",
        "methodology_note": "Individual seller asking price, not a project ASP, transaction, or developer list price. Capture time is not a publisher price-period date."
    }, "parsed-listing"


def fetch_html(session, url):
    if not normal_url(url, listing=False):
        return None, "invalid-host-or-url"
    try:
        response = session.get(url, headers=HEADERS, timeout=15, allow_redirects=True, stream=True)
        if not normal_url(response.url, listing=False):
            response.close()
            return None, "off-host-redirect"
        if response.status_code in (401, 403, 429):
            response.close()
            return None, "access-blocked"
        if response.status_code != 200:
            response.close()
            return None, "http-error"
        if "html" not in response.headers.get("Content-Type", "").lower():
            response.close()
            return None, "non-html-content"
        pieces = []
        used = 0
        for piece in response.iter_content(32768):
            used += len(piece)
            if used > MAX_BYTES:
                response.close()
                return None, "page-too-large"
            pieces.append(piece)
        response.close()
        return b"".join(pieces).decode(response.encoding or "utf-8", errors="replace"), "reachable"
    except requests.RequestException:
        return None, "network-error"


def collect(config, old, session, now, max_per_category=18):
    candidates = {x["candidate_id"]: x for x in old.get("data", [])}
    categories = []
    counts = {}
    inspected = set()
    new_count = 0
    for category in config["categories"]:
        index_html, access = fetch_html(session, category["url"])
        links = discover(index_html, category["url"], max_per_category) if index_html else []
        counts[access] = counts.get(access, 0) + 1
        category_result = {"category_id": category["id"], "index_status": access,
                           "discovered_listing_count": len(links), "listing_checks": 0,
                           "qualified_candidates": 0}
        for url in links:
            if url in inspected:
                continue
            inspected.add(url)
            html, status = fetch_html(session, url)
            if html is None:
                counts[status] = counts.get(status, 0) + 1
                continue
            entry, status = parse_listing(html, url, config["projects"])
            counts[status] = counts.get(status, 0) + 1
            category_result["listing_checks"] += 1
            if entry is None:
                continue
            category_result["qualified_candidates"] += 1
            # Same ad at an unchanged price is one observation, not a new monthly price.
            digest = hashlib.sha256(f"{entry['source_url']}|{entry['listing_price_vnd']}|{entry['area_sqm']}".encode()).hexdigest()[:20]
            identity = "nhatot-listing-" + digest
            if identity not in candidates:
                candidates[identity] = dict(entry, candidate_id=identity, captured_at=now)
                new_count += 1
        categories.append(category_result)
    return ({
        "schema_version": 1, "capture_mode": "scheduled-public-listing-discovery",
        "candidate_only": True, "auto_publish": False, "record_count": min(300, len(candidates)),
        "data": list(candidates.values())[-300:],
        "note": "Never compute parent project averages from these listings automatically."
    }, {
        "schema_version": 1, "generated_at": now,
        "source_id": "nhatot-vn", "categories_checked": len(categories),
        "unique_listings_checked": len(inspected), "new_listing_candidates": new_count,
        "status_counts": counts, "categories": categories,
        "production_changed": False,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg = read(CONFIG, {"categories": [], "projects": {}})
    old = read(QUEUE, {"data": []})
    now = datetime.now(timezone.utc).isoformat()
    queue, result = collect(cfg, old, requests.Session(), now)
    write(REPORT, result)
    write(STATE, result)
    if not args.dry_run:
        write(QUEUE, queue)
    print(json.dumps(result, ensure_ascii=False))
    print("No website, project ASP, or time-series price modified.")


if __name__ == "__main__":
    main()
