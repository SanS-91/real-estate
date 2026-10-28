#!/usr/bin/env python3
"""Read-only monitoring of alternative official/brokerage competitor project sources.

A changed page produces a review alert, never an inferred price, ASP, legal
status, sales/absorption, or a fabricated monthly observation. Stable 200 alone
only confirms the page was reachable from the GitHub runner.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ROOT / "config/market-peer-alternative-targets.json"
STATE = ROOT / "data/state/market-peer-alternative-health.json"
HEADER = {"User-Agent": "RealEstateMarketIntelligence/1.0 (source availability & change watch)"}
IDENTITIES = {
    "izumi-city": re.compile(r"Izumi\\s*(?:City|Canaria)", re.I),
    "aqua-city": re.compile(r"Aqua\s*City", re.I),
    "springville": re.compile(r"Spring\s*Ville", re.I),
    "elyse-island": re.compile(r"Elyse\s*Island", re.I),
    "kita-airport-city": re.compile(r"(?:KITA\s*Airport\s*City|Stella\s*Mega\s*City)", re.I)
}

def load(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback

def valid_target(target):
    url = urlsplit(target.get("url", ""))
    host = target.get("allowed_host")
    return (url.scheme == "https" and bool(host) and url.hostname == host and
            not url.username and not url.password and not url.fragment and
            bool(target.get("id")) and target.get("project_id") in IDENTITIES and
            target.get("price_metric_allowed") is False and
            target.get("source_role") in {"developer-primary", "secondary-brokerage"})

def canonical_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
        tag.decompose()
    main = soup.select_one("main") or soup.select_one("article") or soup.body or soup
    text = re.sub(r"\s+", " ", main.get_text(" ", strip=True))
    return text[:20000]

def observe(target, prior, now, fetcher=None):
    base = {"target_id": target.get("id"), "project_id": target.get("project_id"),
            "source_id": target.get("source_id"), "source_role": target.get("source_role"),
            "watch_scope": target.get("watch_scope"), "url": target.get("url"),
            "checked_at": now.isoformat(), "new_prices_verified": 0,
            "production_prices_written": False}
    oldhash = (prior or {}).get("last_valid_fingerprint")
    oldvalid = (prior or {}).get("last_valid_page_at")
    if not valid_target(target):
        return {**base, "status": "invalid-target", "last_valid_fingerprint": oldhash,
                "last_valid_page_at": oldvalid, "review_required": True}
    try:
        response = fetcher(target["url"]) if fetcher else requests.get(
            target["url"], headers=HEADER, timeout=15, allow_redirects=True)
        actual_url = getattr(response, "url", target["url"])
        real = urlsplit(actual_url)
        if real.scheme != "https" or real.hostname != target["allowed_host"]:
            return {**base, "status": "unexpected-redirect",
                    "http_status": response.status_code, "last_valid_fingerprint": oldhash,
                    "last_valid_page_at": oldvalid, "review_required": True}
        if response.status_code != 200:
            state = "blocked" if response.status_code in {401,403,429} else "http-error"
            return {**base, "status": state, "http_status": response.status_code,
                    "last_valid_fingerprint": oldhash, "last_valid_page_at": oldvalid,
                    "review_required": state != "blocked"}
        page = canonical_text(response.text)
        if len(page) < 80 or not IDENTITIES[target["project_id"]].search(page):
            return {**base, "status": "identity-unverified", "http_status": 200,
                    "last_valid_fingerprint": oldhash, "last_valid_page_at": oldvalid,
                    "review_required": True}
        fingerprint = hashlib.sha256(page.encode("utf-8")).hexdigest()
        changed = bool(oldhash and oldhash != fingerprint)
        first = not oldhash
        return {**base, "status": "content-changed-review" if changed else (
                "baseline-created" if first else "unchanged"),
                "http_status": 200, "source_identity_verified": True,
                "changed_since_previous_valid_check": changed,
                "last_valid_fingerprint": fingerprint,
                "last_valid_page_at": now.isoformat(),
                "review_required": changed,
                "price_publication_status": (
                    "official-price-not-disclosed-vnd-tbu"
                    if target["source_role"] == "developer-primary" and
                    target["project_id"] == "springville" and
                    re.search(r"VND\s*TBU", page, re.I) else "not-verified")
                }
    except requests.RequestException:
        return {**base, "status": "fetch-error", "http_status": None,
                "last_valid_fingerprint": oldhash, "last_valid_page_at": oldvalid,
                "review_required": False}

def build(targets, previous, now, fetcher=None):
    if targets.get("schema_version") != 1:
        raise ValueError("Unsupported alternative peer target schema")
    existing = {row["target_id"]:row for row in previous.get("targets", []) if row.get("target_id")}
    seen=set()
    rows=[]
    for target in targets.get("targets",[]):
        if target.get("id") in seen:
            raise ValueError("Duplicate alternative source target")
        seen.add(target.get("id"))
        rows.append(observe(target, existing.get(target.get("id")), now, fetcher))
    states={}
    for row in rows:
        states[row["status"]]=states.get(row["status"],0)+1
    return {"schema_version":1, "generated_at":now.isoformat(),
            "mode":"alternative-source-access-and-content-change-review",
            "targets_checked":len(rows), "status_counts":states,
            "price_candidates_promoted":0,"source_prices_updated":False,
            "target_coverage_projects":len({x["project_id"] for x in rows}),
            "targets":rows,
            "policy":"Baseline and changes are source-page review alerts only. No prices, sales, absorption or legal status are inferred from page reachability or hash changes."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default=str(STATE))
    args=p.parse_args()
    now=datetime.now(timezone.utc)
    result=build(load(TARGETS, {}),load(STATE, {}),now)
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"targets_checked":result["targets_checked"],
                      "status_counts":result["status_counts"]},ensure_ascii=False))

if __name__=="__main__":
    main()
