"""Alternative publisher monitor: safe access tests and strictly typed candidates.

No attempt to bypass access controls; no in-browser scraping; no automatic
publication to canonical price or Batdongsan listing histories. Historical
launch prices are frozen references. Only explicit new publisher periods can
produce a review-required candidate.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/market-alternative-auto-targets.json"
BASELINE = ROOT / "data/mock/market/alternative-price-evidence.json"
SUBPROJECT_BASELINE = ROOT / "data/mock/market/alternative-subproject-monthly-evidence.json"
REPORT = ROOT / "data/candidate/market/alternative-source-probe-report.json"
CANDIDATES = ROOT / "data/candidate/market/alternative-price-candidates.json"
STATE = ROOT / "data/state/alternative-source-health.json"
QUEUE = ROOT / "data/candidate/market/alternative-price-review-queue.json"
TIMEOUT = 16
MAX_BYTES = 8_000_000
HEADERS = {"User-Agent": "MarketIntelligenceResearchBot/1.0 (public source check)",
           "Accept": "text/html,application/xhtml+xml",
           "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.6"}
PRICE = r"(\d+(?:[.,]\d+)?)"
MONTH_LABEL = re.compile(r"Căn hộ chung cư dự án\s+(.{3,90}?)\s+tháng\s+(\d{1,2})\s*/\s*(20\d{2})", re.I)
MODAL = re.compile(PRICE + r"\s*triệu\s*/?\s*m[²2]", re.I)
MODAL_SECTION = re.compile(r"Đơn giá phổ biến(?P<section>.{0,500}?)Giá thuê phổ biến", re.I)
RANGE = re.compile(r"Khoảng giá\s*[:|]?\s*" + PRICE + r"\s*[-–]\s*" + PRICE + r"\s*triệu", re.I)
REVER_DATE = re.compile(r"Cập nhật\s*[:|]?\s*(\d{2})/(\d{2})/(20\d{2})", re.I)
REVER_PRICE = re.compile(PRICE + r"\s*triệu\s*/?\s*m[²2]", re.I)
CHALLENGE = re.compile(r"just a moment|attention required|checking your browser|verify you are human|captcha|cloudflare challenge", re.I)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def vnd(raw):
    return int(round(float(raw.replace(",", ".")) * 1_000_000))


def plain_text(html):
    soup = BeautifulSoup(html, "lxml")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def source_hostname(url):
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    return host


def publisher_hosts(source_id):
    return {
        "onehousing-vn": {"onehousing.vn", "beta.onehousing.vn"},
        "rever-vn": {"rever.vn", "blog.rever.vn"},
    }.get(source_id, set())


def allowed_target(target):
    url = urlsplit(target["url"])
    return (url.scheme == "https" and not url.username and not url.password
            and not url.query and not url.fragment
            and source_hostname(target["url"]) in publisher_hosts(target["source_id"]))


def normal_name(text):
    value = unicodedata.normalize("NFKD", text.lower().replace("đ", "d"))
    return re.sub(r"\s+", " ", "".join(c for c in value if not unicodedata.combining(c))).strip()


def onehousing_monthly(text, today, publisher_project_name="Vinhomes Grand Park"):
    """Match EXACT source-authored apartment project name, month, and modal price section.

    Never reassign a Lumière/Masteri subproject value to the parent Vinhomes
    Grand Park series. Do not use a crawler/check date as a monthly period.
    """
    for header in MONTH_LABEL.finditer(text):
        if normal_name(header.group(1)) != normal_name(publisher_project_name):
            continue
        month, year = int(header.group(2)), int(header.group(3))
        if not 1 <= month <= 12:
            continue
        period = f"{year:04d}-{month:02d}"
        if period > today.strftime("%Y-%m"):
            continue
        block = text[header.end():header.end() + 9000]
        section = MODAL_SECTION.search(block)
        if not section or section.start() > 6000:
            continue
        modal = MODAL.search(section.group("section"))
        range_match = RANGE.search(section.group("section"))
        if not (modal and range_match):
            continue
        value, low, high = vnd(modal.group(1)), vnd(range_match.group(1)), vnd(range_match.group(2))
        if not (0 < low <= value <= high <= 1_000_000_000):
            continue
        return {
            "period": period,
            "value_vnd_per_m2": value,
            "range_low_vnd_per_m2": low,
            "range_high_vnd_per_m2": high,
            "evidence": {
                "period": header.group(0),
                "metric": modal.group(0),
                "range": range_match.group(0),
            },
        }
    return None


def onehousing_source_diagnostics(text,publisher_project_name):
    """Small, non-sensitive parser hints for public runner HTML (never store full page)."""
    headers=[f"{m.group(3)}-{int(m.group(2)):02d}" for m in MONTH_LABEL.finditer(text)
             if normal_name(m.group(1))==normal_name(publisher_project_name)]
    return {
        "publisher_project_header":bool(headers),
        "publisher_periods":sorted(set(headers)),
        "modal_price_section":bool(MODAL_SECTION.search(text)),
        "asking_price_number":bool(MODAL.search(text)),
        "asking_range_number":bool(RANGE.search(text)),
        "login_wall_in_text":"Đăng nhập để xem giá" in text,
    }


def rever_single_listing(text, today):
    if "Vinhomes Grand Park" not in text or not re.search(r"\b69\s*m[²2]\b", text, re.I):
        return None
    match_date = REVER_DATE.search(text)
    if not match_date:
        return None
    try:
        publication = date(int(match_date.group(3)), int(match_date.group(2)), int(match_date.group(1)))
    except ValueError:
        return None
    if publication > today:
        return None
    # The price must be anchored near the expected apartment unit description.
    unit_pos = re.search(r"\b69\s*m[²2]\b", text, re.I)
    window = text[max(0, unit_pos.start() - 250):unit_pos.end() + 300]
    prices = list(REVER_PRICE.finditer(window))
    if len(prices) != 1:
        return None
    return {
        "period": publication.isoformat(),
        "value_vnd_per_m2": vnd(prices[0].group(1)),
        "range_low_vnd_per_m2": None,
        "range_high_vnd_per_m2": None,
        "evidence": {
            "period": match_date.group(0),
            "metric": prices[0].group(0),
            "unit": "Căn hộ Vinhomes Grand Park · 69m²",
        },
    }


def classify(target, html, baseline, today):
    text = plain_text(html)
    if len(text) < 100 or CHALLENGE.search(text[:900]):
        return "blocked-or-empty-page", None
    mode = target["mode"]
    if mode == "historical-reference-monitor":
        return "reachable-historical-reference-frozen", None
    parsed = (onehousing_monthly(text, today, target.get("publisher_project_name", "Vinhomes Grand Park")) if mode == "monthly-price-candidate"
              else rever_single_listing(text, today) if mode == "single-listing-review"
              else None)
    if parsed is None:
        return "reachable-no-verifiable-metric", None
    old_period = baseline["period"]
    if parsed["period"] < old_period:
        return "older-period-no-candidate", None
    if parsed["period"] == old_period:
        unchanged = (all(parsed[k] == baseline.get(k) for k in
                         ("value_vnd_per_m2", "range_low_vnd_per_m2", "range_high_vnd_per_m2")))
        return ("same-period-unchanged" if unchanged else "same-period-review-required"), None
    # Independent publication period is required. This is NEVER auto-promoted.
    row = {k: baseline.get(k) for k in
           ("project_id", "source_id", "source_url", "asset_type",
            "metric_type", "period_type", "subproject_name") if k in baseline}
    row.update(parsed)
    row.update({
        "id": "candidate-" + target["target_id"] + "-" + parsed["period"],
        "source_url": target["url"],
        "source_publication_date": parsed["period"] if target["period_type"] == "date" else None,
        "review_date": None,
        "candidate_only": True,
        "review_required": True,
        "collection_mode": "github-runner-public-html",
        "baseline_record_id": baseline["id"],
        "methodology_note": "New independent publisher period requires human evidence review. Never blend source metrics or use single listing as project ASP.",
    })
    return "new-period-review-required", row


def fetch_html(target, session):
    if not allowed_target(target):
        return {"status": "invalid-source-url"}, None
    try:
        resp = session.get(target["url"], headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True)
        code = resp.status_code
        final_url = resp.url
        result = {"http_status": code, "final_host": source_hostname(final_url)}
        if source_hostname(final_url) not in publisher_hosts(target["source_id"]):
            resp.close()
            return dict(result, status="redirect-off-publisher"), None
        if code in (401, 403, 429):
            resp.close()
            return dict(result, status="blocked"), None
        if code != 200:
            resp.close()
            return dict(result, status="http-error"), None
        if "html" not in resp.headers.get("Content-Type", "").lower():
            resp.close()
            return dict(result, status="non-html"), None
        chunks, size = [], 0
        for chunk in resp.iter_content(chunk_size=32768):
            size += len(chunk)
            if size > MAX_BYTES:
                resp.close()
                return dict(result, status="too-large"), None
            chunks.append(chunk)
        resp.close()
        return dict(result, status="reachable"), b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
    except requests.RequestException as error:
        return {"status": "fetch-error", "error_type": error.__class__.__name__}, None



def fetch_with_publisher_fallback(target, session):
    """On a publisher login/JS-only variant, inspect an explicitly pinned official mirror.

    Mirror must be the exact same project slug and ID on an allowed OneHousing
    host. Never bypass a block or treat an unlabelled numeric value as evidence.
    """
    status,html=fetch_html(target,session)
    if html and target.get("mode")=="monthly-price-candidate":
        if onehousing_monthly(plain_text(html),date.today(),
                             target.get("publisher_project_name","Vinhomes Grand Park")):
            return status,html
    for url in target.get("fallback_urls",[]):
        main=urlsplit(target["url"])
        mirror=urlsplit(url)
        if (mirror.path!=main.path or mirror.scheme!="https" or
            mirror.hostname not in publisher_hosts(target["source_id"]) or
            mirror.query or mirror.fragment):
            continue
        alt={**target,"url":url}
        details,page=fetch_html(alt,session)
        if page and onehousing_monthly(plain_text(page),date.today(),
                                      target.get("publisher_project_name","Vinhomes Grand Park")):
            return dict(details,fallback_used=True,checked_url=url),page
    return status,html


def run(targets, baselines, today, session, fetcher=fetch_html):
    checks, candidates = [], []
    for target in targets:
        prior = baselines.get(target["baseline_id"])
        row = {
            "target_id": target["target_id"], "source_id": target["source_id"],
            "project_id": target["project_id"], "mode": target["mode"],
            "baseline_period": prior.get("period") if prior else None,
        }
        if not prior or not allowed_target(target) or (prior["project_id"], prior["source_id"], prior["source_url"], prior["metric_type"]) != (
                target["project_id"], target["source_id"], target["url"], target["metric_type"]) or (target.get("subproject_name") and prior.get("subproject_name") != target["subproject_name"]):
            row["status"] = "invalid-target-mapping"
        else:
            probe, html = (fetch_with_publisher_fallback(target,session)
                           if fetcher is fetch_html else fetcher(target,session))
            row.update(probe)
            if html is not None:
                status, candidate = classify(target, html, prior, today)
                row["status"] = status
                if status == "reachable-no-verifiable-metric" and target.get("mode") == "monthly-price-candidate":
                    row["parser_diagnostics"] = onehousing_source_diagnostics(
                        plain_text(html), target.get("publisher_project_name","Vinhomes Grand Park"))
                if candidate:
                    candidates.append(candidate)
        checks.append(row)
    return checks, candidates


def append_review_queue(queue, detected):
    """Append-only candidate queue; never rewrite an older unreviewed observation."""
    existing = {r["id"]: r for r in queue.get("data", [])}
    added, conflicts = 0, 0
    for row in detected:
        previous = existing.get(row["id"])
        if previous is None:
            queue["data"].append(row)
            existing[row["id"]] = row
            added += 1
        elif any(previous.get(field) != row.get(field) for field in
                 ("period", "source_url", "metric_type", "value_vnd_per_m2",
                  "range_low_vnd_per_m2", "range_high_vnd_per_m2")):
            conflicts += 1
    queue["record_count"] = len(queue["data"])
    return added, conflicts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", default=date.today().isoformat())
    args = parser.parse_args()
    today = date.fromisoformat(args.today)
    config = load(CONFIG)
    baseline = {r["id"]: r for r in (load(BASELINE)["data"] + load(SUBPROJECT_BASELINE)["data"])}
    checks, candidates = run(config["targets"], baseline, today, requests.Session())
    queue = load(QUEUE) if QUEUE.exists() else {
        "schema_version": 1, "candidate_only": True, "review_required": True, "data": []}
    new_queue_rows, queue_conflicts = append_review_queue(queue, candidates)
    if new_queue_rows or not QUEUE.exists():
        save(QUEUE, queue)
    timestamp = datetime.now(timezone.utc).isoformat()
    counts = {status: sum(x["status"] == status for x in checks) for status in sorted({x["status"] for x in checks})}
    report = {
        "schema_version": 1, "generated_at": timestamp,
        "targets_checked": len(checks), "candidates_staged": len(candidates),
        "queued_new": new_queue_rows, "queued_backlog": queue["record_count"],
        "queue_conflicts": queue_conflicts,
        "counts": counts, "checks": checks, "production_written": False,
        "source_prices_not_inferred": True,
        "note": "No access bypass. Candidate-only; source dates and metric types must pass manual source review before publication.",
    }
    save(REPORT, report)
    save(CANDIDATES, {
        "schema_version": 1, "generated_at": timestamp, "candidate_only": True,
        "record_count": len(candidates), "data": candidates,
    })
    save(STATE, {
        "schema_version": 1, "generated_at": timestamp, "targets_checked": len(checks),
        "candidate_count": len(candidates), "queue_backlog": queue["record_count"],
        "queue_conflicts": queue_conflicts, "production_updated": False,
        "counts": counts, "checks": checks,
    })
    print(json.dumps({"checked": len(checks), "candidates": len(candidates), "queue_backlog": queue["record_count"], "conflicts": queue_conflicts, "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
