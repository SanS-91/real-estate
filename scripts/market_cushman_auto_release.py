"""Phase 4H: automatic, source-authored Cushman quarterly apartment observations.

A new reporting quarter is published only after two independent hosted runs
>=1 hour apart reproduce the same exact primary-market apartment figures.
No inferred dates, no currency conversions, no derived project prices.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from market_quarterly_source_period import source_quarter

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.cushmanwakefield.com/en/vietnam/insights/ho-chi-minh-city-marketbeat/residential-marketbeat"
HISTORY = ROOT / "data/mock/market/observations.json"
STATE = ROOT / "data/state/market-cushman-quarterly-verification.json"
REPORT = ROOT / "data/candidate/market/market-cushman-quarterly-release-report.json"
USER_AGENT = "MarketIntelligenceResearchBot/1.0 (public quarterly source check)"
SOURCE_ID = "cushman-wakefield-vietnam-market"
MAX_HISTORY = 14
MAX_BYTES = 5_000_000


def read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fetch(session):
    try:
        response = session.get(URL, headers={
            "User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        }, timeout=20, stream=True, allow_redirects=True)
        if response.url.rstrip("/") != URL:
            response.close()
            return None, "source-redirect-mismatch"
        if response.status_code in (401, 403, 429):
            response.close()
            return None, "access-blocked"
        if response.status_code != 200:
            response.close()
            return None, "http-error"
        if "html" not in response.headers.get("Content-Type", "").lower():
            response.close()
            return None, "not-html"
        chunks = []
        length = 0
        for part in response.iter_content(chunk_size=32768):
            length += len(part)
            if length > MAX_BYTES:
                response.close()
                return None, "source-too-large"
            chunks.append(part)
        response.close()
        return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace"), "reachable"
    except requests.RequestException:
        return None, "source-network-error"


def extract(html, now):
    quarter = source_quarter(html)
    period = quarter.get("period")
    if not period:
        return None, quarter.get("status", "no-source-quarter")
    current = now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
    latest_allowed = f"{current.year}-Q{(current.month - 1) // 3 + 1}"
    if period > latest_allowed or period < "2026-Q2":
        return None, "publisher-quarter-outside-valid-range"
    soup = BeautifulSoup(html, "lxml")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    start = re.search(r"\bAPARTMENT FOR SALE\b", text, re.I)
    end = re.search(r"\bLANDED PROPERTY\b", text, re.I)
    if not start or not end or end.start() <= start.end():
        return None, "apartment-section-not-bounded"
    apartment = text[start.end():end.start()]
    supply = re.search(r"new supply[^.]{0,250}?over\s*([\d,]+)\s*units", apartment, re.I)
    absorption = re.search(r"absorption rate of\s*([\d.]+)%\s*of newly launched primary supply", apartment, re.I)
    if not (supply and absorption):
        return None, "insufficient-explicit-apartment-metrics"
    lower = int(supply.group(1).replace(",", ""))
    rate = float(absorption.group(1)) / 100
    if not (100 <= lower <= 100000 and 0 < rate < 1):
        return None, "implausible-reported-metrics"
    return {
        "period": period, "new_supply_lower_bound": lower,
        "absorption_rate": rate,
        "evidence": {"quarter": quarter["evidence"],
                     "supply": supply.group(0)[:250],
                     "absorption": absorption.group(0)[:200]}
    }, "matched-source-quarter-and-metrics"


def digest(candidate):
    return hashlib.sha256(json.dumps(
        [candidate.get("period"), candidate.get("new_supply_lower_bound"),
         candidate.get("absorption_rate"), URL],
        separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def check(history, previous, html, now, run_id):
    """Pure decision over persisted source checks; no filesystem or HTTP effects."""
    record = extract(html, now)[0] if html is not None else None
    status = extract(html, now)[1] if html is not None else "source-fetch-failed"
    checks = list(previous.get("checks", []))
    if not any(x.get("run_id") == str(run_id) for x in checks):
        checks.append({
            "run_id": str(run_id), "checked_at": now.isoformat(),
            "status": status, "period": record.get("period") if record else None,
            "signature": digest(record) if record else None,
        })
    checks = checks[-MAX_HISTORY:]
    output = {"schema_version": 1, "source_id": SOURCE_ID, "source_url": URL,
              "latest_status": status, "checks": checks,
              "note": "Only source-published reporting quarters; check time is not a price publication date."}
    if record is None:
        return output, None, "no-verified-metrics"
    rows = [x for x in history if x.get("source_id") == SOURCE_ID and
            x.get("scope_type") == "region-segment" and x.get("segment_ids") == ["apartment"]]
    old_periods = {x.get("period"): x for x in rows}
    if record["period"] in old_periods:
        existing = old_periods[record["period"]]
        if existing.get("new_supply_lower_bound") == record["new_supply_lower_bound"] and abs(
                (existing.get("absorption_rate") or 0) - record["absorption_rate"]) < .000001:
            return output, None, "already-published"
        return output, None, "source-conflict-with-published-quarter"
    latest = max(rows, key=lambda x: x.get("period", ""), default=None)
    if latest and record["period"] <= latest.get("period", ""):
        return output, None, "older-than-published-quarter"
    pair = checks[-2:]
    if len(pair) != 2 or any(x["status"] != "matched-source-quarter-and-metrics"
                               or x["signature"] != digest(record)
                               for x in pair):
        return output, None, "need-two-consecutive-source-matches"
    if pair[0]["run_id"] == pair[1]["run_id"]:
        return output, None, "same-run-cannot-confirm"
    try:
        first = datetime.fromisoformat(pair[0]["checked_at"])
        second = datetime.fromisoformat(pair[1]["checked_at"])
        if first.tzinfo is None or second.tzinfo is None or second - first < timedelta(hours=1):
            return output, None, "checks-under-one-hour-apart"
    except (TypeError, ValueError, KeyError):
        return output, None, "invalid-check-timestamps"
    if latest:
        if abs(record["absorption_rate"] - (latest.get("absorption_rate") or 0)) > .30:
            return output, None, "absorption-jump-review-required"
        lower_prev = latest.get("new_supply_lower_bound") or latest.get("new_supply")
        if lower_prev and record["new_supply_lower_bound"] > 4 * lower_prev:
            return output, None, "supply-outlier-review-required"
    row = {
        "id": f"obs-hcmc-apartment-{record['period'].lower()}-cushman",
        "scope_type": "region-segment", "region_ids": ["hcmc"],
        "segment_ids": ["apartment"],
        "period": record["period"], "period_type": "quarter",
        "new_supply": None, "new_supply_lower_bound": record["new_supply_lower_bound"],
        "sales_units": None, "absorption_rate": record["absorption_rate"],
        "average_asp": None, "asp_unit": "vnd-per-m2", "currency": "VND",
        "price_basis": None,
        "metric_qualifiers": {"new_supply_lower_bound": "greater-than", "absorption_rate": "exact"},
        "source_id": SOURCE_ID, "source_date": None, "source_url": URL,
        "source_evidence": record["evidence"],
        "verification_run_ids": [x["run_id"] for x in pair],
        "review_status": "automated-source-verified",
        "methodology_note": (
            "Cushman & Wakefield HCMC Residential MarketBeat source-authored "
            f"{record['period']}: apartment new supply exceeds "
            f"{record['new_supply_lower_bound']:,} units; reported absorption "
            f"{record['absorption_rate']:.0%}. Lower bound is not an exact supply count. "
            "Two independent publisher reads >=1h apart. No price or source publication date inferred."
        ),
    }
    return output, row, "two-independent-quarterly-metrics-verified"


def main():
    html, access = fetch(requests.Session())
    now = datetime.now(timezone.utc)
    previous = read(STATE, {})
    production = read(HISTORY, {"data": []})
    state, candidate, result = check(production.get("data", []), previous, html, now,
                                     os.environ.get("GITHUB_RUN_ID", now.isoformat()))
    state["access_status"] = access
    write(STATE, state)
    if candidate:
        production["data"].append(candidate)
        production["data"].sort(key=lambda row: (row.get("scope_type", ""),
                                                 row.get("period", ""), row.get("id", "")))
        production["record_count"] = len(production["data"])
        production["generated_at"] = now.isoformat()
        production["build_id"] = "market-quarterly-verified-" + now.strftime("%Y%m%dT%H%M%SZ")
        write(HISTORY, production)
    report = {"schema_version": 1, "checked_at": now.isoformat(),
              "status": result, "access": access,
              "production_written": bool(candidate),
              "candidate_period": candidate["period"] if candidate else None,
              "check_count": len(state["checks"])}
    write(REPORT, report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
