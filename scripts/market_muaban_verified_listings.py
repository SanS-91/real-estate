"""Phase 4I.6: Muaban public sale listings; expiry-gated, project-scoped.

Separate from Rever/OneHousing. A relative "updated today" is NOT evidence
of a valid listing when the publisher's explicit expiration has passed.
Only two independent scheduled GitHub checks >=1h apart may publish an
individually attributed apartment offer. Never aggregate into project ASP.
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
CONFIG = ROOT / "config/market-muaban-listing-targets.json"
STATE = ROOT / "data/state/market-muaban-listing-verification.json"
OUTPUT = ROOT / "data/mock/market/verified-muaban-unit-listings.json"
HEALTH = ROOT / "data/state/market-muaban-source-health.json"
REPORT = ROOT / "data/candidate/market/muaban-listing-report.json"
HOST = "muaban.net"
MAX_LINKS = 12
MAX_AGE = 90
MAX_CHECKS = 8
MAX_BYTES = 3_000_000
DATE_RX = r"(\d{2})/(\d{2})/(20\d{2})"
ID_RX = re.compile(r"(?:^|[-/])id(\d{6,12})$", re.I)
BLOCK = re.compile(r"tin hết hạn|đã bán|đã gỡ|không còn bán", re.I)
PRICE = re.compile(r"(\d+(?:[,.]\d+)?)\s*tỷ\b", re.I)
AREA = re.compile(r"(\d+(?:[,.]\d+)?)\s*m[²2]\b", re.I)
HEADERS = {
    "User-Agent": "MarketIntelligenceResearchBot/1.0 (public research evidence check)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "vi-VN,vi;q=0.9",
}


def load(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_url(url, listing=False):
    u = urlsplit(str(url))
    if (u.scheme != "https" or u.hostname not in (HOST, "www." + HOST)
            or u.username or u.password or u.port not in (None, 443)
            or u.query or u.fragment):
        return None
    path = u.path.rstrip("/")
    if not path.startswith("/bat-dong-san/ban-can-ho"):
        return None
    if listing and not ID_RX.search(path):
        return None
    if not listing and ID_RX.search(path):
        return None
    return f"https://{HOST}{path}"


def discover(html, catalog_url):
    if not html or not safe_url(catalog_url, False):
        return []
    seen = []
    for a in BeautifulSoup(html, "lxml").select("a[href]"):
        uri = safe_url(urljoin(catalog_url, a.get("href", "")), listing=True)
        if uri and uri not in seen:
            seen.append(uri)
        if len(seen) >= MAX_LINKS:
            break
    return seen


def iso_date(raw):
    match = re.search(DATE_RX, raw or "")
    if not match:
        return None
    try:
        return date(int(match[3]), int(match[2]), int(match[1]))
    except ValueError:
        return None


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().casefold()


def after_label(lines, name):
    """Extract a labeled value in a source detail block, not a site-wide guess."""
    pattern = re.compile(r"^" + re.escape(name) + r"\s*:?\s*(.*)$", re.I)
    candidates = []
    for i, line in enumerate(lines):
        m = pattern.match(line.strip())
        if m:
            tail = m.group(1).strip() or (lines[i + 1].strip() if i + 1 < len(lines) else "")
            candidates.append(tail)
    return candidates[0] if len(candidates) == 1 else None


def parse_detail(html, url, project_name, project_id, now):
    valid = safe_url(url, listing=True)
    if not valid or not html:
        return None, "unsafe-or-empty"
    soup = BeautifulSoup(html, "lxml")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    title_node = soup.find("h1")
    if not title_node:
        return None, "missing-detail-header"
    title = title_node.get_text(" ", strip=True)
    if re.search(r"cho thuê|thuê căn hộ|đất nền|nhà phố|officetel", title, re.I):
        return None, "non-apartment-or-rental"
    # Publisher metadata from the detail's first heading onward. Ignore
    # recommendations below the page's own listing metadata.
    raw = "\n".join(n.strip() for n in title_node.next_elements
                    if isinstance(n, str) and n.strip())
    if "Thông tin cơ bản" not in raw or "Ngày bắt đầu" not in raw:
        return None, "missing-publisher-detail-fields"
    raw = raw[:24000]
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    first = raw.split("Thông tin chi tiết")[0]
    # Dynamic time badges are not publisher-dated validity.
    amount = PRICE.search(first[:1600])
    if not amount:
        return None, "missing-numeric-total-sale-price"
    try:
        value = float(amount.group(1).replace(",", "."))
    except ValueError:
        return None, "invalid-price"
    if not 0.4 <= value <= 250:
        return None, "implausible-price"
    # Reject "giỏ hàng"/price-list ads which attach several sale prices to a
    # single detail page: their page area and headline price need not refer to
    # the same apartment. Never infer an individual-unit rate from those ads.
    detail_section = raw.split("Thông tin chi tiết", 1)[1].split("Thông tin cơ bản", 1)[0]
    stated_prices = {round(float(v.replace(",", ".")), 5) for v in PRICE.findall(detail_section)}
    if len(stated_prices) > 1:
        return None, "multiple-sale-price-claims"
    # Only the listing's own basic-information section may establish its
    # project; an unrelated recommendation or category page is insufficient.
    basic = raw.split("Thông tin cơ bản", 1)[1].split("Thông tin dự án", 1)[0]
    basic_lines = [x.strip() for x in basic.splitlines() if x.strip()]
    # HTML publisher badges often put labels, colons and values in separate
    # nodes. Normalize whitespace *inside the source's own basic-info block*
    # only; never use the category, title or recommended projects as proof.
    basic_flat = " ".join(basic_lines)
    boundaries = (
        r"Loại hình căn hộ|Loại hình bất động sản|Dự án|Diện tích sử dụng|"
        r"Số phòng ngủ|Số phòng vệ sinh|Hướng cửa chính|Hướng ban công|"
        r"Giấy tờ pháp lý|Tầng số"
    )
    def basic_value(label):
        matches = re.findall(
            r"(?:^|\s)" + re.escape(label) +
            r"\s*:\s*(.+?)(?=\s+(?:" + boundaries + r")\s*:|$)",
            basic_flat, re.I)
        return matches[0].strip() if len(matches) == 1 else None

    project = basic_value("Dự án")
    if not project or norm(project) != norm(project_name):
        return None, "project-not-explicit"
    product = basic_value("Loại hình căn hộ") or basic_value("Loại hình bất động sản")
    if not product or not re.search(r"chung cư|căn hộ", product, re.I):
        return None, "wrong-product-type"
    area_text = basic_value("Diện tích sử dụng")
    sqm_match = AREA.search(area_text or "")
    if not sqm_match:
        return None, "missing-area"
    sqm = float(sqm_match.group(1).replace(",", "."))
    if not 25 <= sqm <= 450:
        return None, "invalid-area"
    # Dates MUST come from the publisher's actual start/expiry fields.
    # "Cập nhật: Hôm nay" cannot override an expired posting.
    def scoped_date(label):
        values = re.findall(
            re.escape(label) + r"\s*:?\s*" + DATE_RX, raw, re.I)
        return date(int(values[0][2]), int(values[0][1]), int(values[0][0])) if len(values) == 1 else None

    try:
        start, expiry = scoped_date("Ngày bắt đầu"), scoped_date("Ngày hết hạn")
    except ValueError:
        start, expiry = None, None
    if not start or not expiry or expiry < start:
        return None, "incomplete-or-conflicting-validity"
    if now.date() > expiry:
        return None, "publisher-expired"
    if start > now.date():
        return None, "future-start"
    if (now.date() - start).days > MAX_AGE:
        return None, "older-than-90-day-start"
    listing_id = ID_RX.search(valid).group(1)
    ids = re.findall(r"Mã tin\s*:?\s*(\d{6,12})(?!\d)", raw, re.I)
    if len(ids) != 1 or ids[0] != listing_id:
        return None, "listing-id-mismatch"
    # "Tin hết hạn" sometimes appears as an image badge. Restrict to explicit
    # publisher status within listing header, and retain absolute expiry as
    # mandatory even when no such badge appears.
    if BLOCK.search(first[:1800]):
        return None, "publisher-marked-unavailable"
    vnd = round(value * 1_000_000_000)
    unit = round(vnd / sqm)
    if not 5_000_000 <= unit <= 700_000_000:
        return None, "implausible-unit-price"
    return {
        "project_id": project_id, "project_name": project_name,
        "source_id": "muaban-vn", "source_url": valid,
        "listing_id": listing_id, "listing_title": title[:160],
        "asset_type": "apartment", "market_layer": "individual-listing-asking",
        "metric_type": "single-listing-asking-price-per-sqm",
        "source_date_basis": "publisher-listing-start-not-update",
        "source_listed_date": start.isoformat(),
        "source_updated_date": start.isoformat(),
        "source_expiration_date": expiry.isoformat(),
        "listed_area_sqm": sqm, "listing_price_vnd": vnd,
        "value_vnd_per_m2": unit,
        "unit_price_basis": "derived-from-advertised-total-and-area",
        "source_publication_date": None,
        "methodology_note": (
            "Individual Muaban asking advertisement only. The displayed rate "
            "is calculated from the listing's advertised total and usable area, "
            "not a publisher average, transaction, project ASP or project range. "
            "Date displayed is listing START date, NOT its relative update badge. "
            "Use only while the publisher's end date is unexpired."
        )
    }, "qualified-unexpired-listing"


def fetch(session, url, listing=False):
    if not safe_url(url, listing=listing):
        return None, "invalid-url"
    try:
        r = session.get(url, timeout=18, stream=True, headers=HEADERS,
                        allow_redirects=True)
        if not safe_url(r.url, listing=listing):
            r.close()
            return None, "untrusted-redirect"
        if r.status_code in (401, 403, 429):
            r.close()
            return None, "access-blocked"
        if r.status_code != 200 or "html" not in r.headers.get("Content-Type", "").lower():
            r.close()
            return None, "http-or-format-error"
        chunks, length = [], 0
        for chunk in r.iter_content(32768):
            length += len(chunk)
            if length > MAX_BYTES:
                r.close()
                return None, "oversized-response"
            chunks.append(chunk)
        r.close()
        return b"".join(chunks).decode(r.encoding or "utf-8", "replace"), "reachable"
    except requests.RequestException:
        return None, "connection-error"


def fingerprint(row):
    fields = ("project_id", "source_url", "listing_id", "source_listed_date",
              "source_expiration_date", "listing_price_vnd",
              "listed_area_sqm", "value_vnd_per_m2")
    return hashlib.sha256(json.dumps([row[x] for x in fields]).encode()).hexdigest()


def evaluate(previous, published, valid_rows, now, run_id):
    state = {x["listing_id"]: x for x in previous.get("listings", [])}
    recorded = {fingerprint(x) for x in published}
    accepted, decisions = [], []
    for row in valid_rows:
        sig = fingerprint(row)
        stored = state.get(row["listing_id"], {})
        checks = stored.get("checks", [])
        if not any(x["run_id"] == str(run_id) for x in checks):
            checks = (checks + [{
                "run_id": str(run_id), "checked_at": now.isoformat(),
                "fingerprint": sig, "expiry": row["source_expiration_date"],
            }])[-MAX_CHECKS:]
        state[row["listing_id"]] = {
            "listing_id": row["listing_id"], "project_id": row["project_id"],
            "source_url": row["source_url"], "checks": checks,
        }
        outcome = "await-independent-hosted-check"
        if sig in recorded:
            outcome = "already-published"
        elif len(checks) >= 2 and checks[-1]["fingerprint"] == checks[-2]["fingerprint"] and checks[-1]["run_id"] != checks[-2]["run_id"]:
            try:
                older, newer = (datetime.fromisoformat(x["checked_at"]) for x in checks[-2:])
                if older.tzinfo and newer.tzinfo and newer - older >= timedelta(hours=1):
                    accepted.append({
                        **row, "id": "muaban-" + row["listing_id"] + "-" + sig[:12],
                        "review_status": "automated-two-hosted-checks",
                        "review_date": now.date().isoformat(),
                        "verification_run_ids": [x["run_id"] for x in checks[-2:]],
                        "verified_at": now.isoformat(),
                    })
                    outcome = "independent-current-ad-verified"
                else:
                    outcome = "checks-under-one-hour"
            except (KeyError, ValueError, TypeError):
                outcome = "invalid-check-timestamps"
        decisions.append({
            "listing_id": row["listing_id"], "project_id": row["project_id"],
            "decision": outcome,
        })
    return {
        "schema_version": 1,
        "listings": sorted(state.values(), key=lambda x: x["listing_id"]),
    }, accepted, decisions


def scan(config, published, previous, get, now, run_id, publish=True):
    rows, seen, sources = [], set(), []
    for target in config.get("targets", []):
        pid, project, url = (target.get("project_id"),
                             target.get("publisher_project_name"),
                             target.get("url", ""))
        if not pid or not project or not safe_url(url):
            sources.append({"project_id": pid, "access": "invalid-target",
                            "discovered": 0, "checked": 0, "qualified": 0,
                            "reasons": {}})
            continue
        catalog, access = get(url, False)
        urls = discover(catalog, url)
        result = {"project_id": pid, "source_url": url, "access": access,
                  "discovered": len(urls), "checked": 0,
                  "qualified": 0, "reasons": {}}
        for link in urls:
            if link in seen:
                continue
            seen.add(link)
            content, status = get(link, True)
            result["checked"] += 1
            row, reason = ((None, status) if not content else
                           parse_detail(content, link, project, pid, now))
            result["reasons"][reason] = result["reasons"].get(reason, 0) + 1
            if row:
                result["qualified"] += 1
                rows.append(row)
        sources.append(result)
    if publish:
        state, newly_accepted, decisions = evaluate(
            previous, published.get("data", []), rows, now, run_id)
    else:
        state, newly_accepted = previous, []
        decisions = [{"listing_id": x["listing_id"],
                      "decision": "pr-diagnostic-only"} for x in rows]
    output = {
        "schema_version": 1, "collection_mode": "two-hosted-checks-unexpired-unit-asking",
        "data": (published.get("data", []) + newly_accepted)[-250:],
    }
    output["record_count"] = len(output["data"])
    health = {
        "schema_version": 1, "generated_at": now.isoformat(),
        "source_id": "muaban-vn", "targets_checked": len(sources),
        "listing_urls_discovered": sum(x["discovered"] for x in sources),
        "details_checked": sum(x["checked"] for x in sources),
        "valid_unexpired_project_ads": len(rows),
        "newly_published": len(newly_accepted),
        "published_current_individual_listings": sum(
            x.get("review_status") == "automated-two-hosted-checks"
            and bool(x.get("source_expiration_date"))
            and x["source_expiration_date"] >= now.date().isoformat()
            for x in output["data"]
        ),
        "sources": sources,
        "publication_enabled": publish,
        "no_project_asp_or_range": True,
        "date_policy": "start-and-expiry-only; relative update badges are not validity evidence",
    }
    return output, state, health, decisions


def main():
    config = load(CONFIG, {"targets": []})
    previous = load(STATE, {})
    output = load(OUTPUT, {"data": []})
    now = datetime.now(timezone.utc)
    pr = os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
    session = requests.Session()
    result, state, health, decisions = scan(
        config, output, previous, lambda url, listing: fetch(session, url, listing),
        now, os.environ.get("GITHUB_RUN_ID", now.isoformat()), publish=not pr)
    save(REPORT, {**health, "decisions": decisions})
    if not pr:
        save(OUTPUT, result)
        save(STATE, state)
        save(HEALTH, health)
    print(json.dumps(health, ensure_ascii=False))


if __name__ == "__main__":
    main()
