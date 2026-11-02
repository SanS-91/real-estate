#!/usr/bin/env python3
"""Official landed-project source monitor: source changes ONLY, never price data.

Uses public project/issuer URLs, respects access failures, and does not try to
bypass rate limits. A changing page is a *review lead*, not a new price or sale.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/market-landed-source-watch.json"
PROJECTS = ROOT / "data/mock/market/projects.json"
STATE = ROOT / "data/state/market-landed-source-health.json"
HEADERS = {"User-Agent": "MarketIntelligenceResearchBot/1.0 (public source status monitoring)"}
MAX_BYTES = 1_500_000

def load(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def permitted(url: str, expected_host: str):
    x = urlsplit(url)
    actual = (x.hostname or "").lower().removeprefix("www.")
    return (x.scheme == "https" and not x.username and not x.password
            and not x.query and not x.fragment and actual == expected_host)

def text_fingerprint(html: str, project_name: str = "", page_type: str = "project-landing",
                     title_hint: str = ""):
    """Return stable body fingerprint and the matching publisher heading.

    For a developer news article, permit a project-specific H2/H3 when the
    publisher's generic H1 is a site category. Never infer price from text.
    """
    soup = BeautifulSoup(html, "lxml")
    for node in soup(["script", "style", "nav", "footer", "noscript"]):
        node.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    body = re.sub(r"\s+", " ", main.get_text(" ", strip=True))
    headings = [re.sub(r"\s+", " ", h.get_text(" ", strip=True))
                for h in main.find_all(["h1", "h2", "h3"], limit=15)]
    name = project_name.casefold()
    if page_type == "project-news-article" and title_hint:
        matching = [h for h in headings if name in h.casefold()
                    and title_hint.casefold() in h.casefold()]
    elif project_name:
        matching = [h for h in headings if name in h.casefold()]
    else:
        matching = headings[:1]
    headline = matching[0][:240] if matching else ""
    if len(body) < 150 or not headline:
        return None, headline
    return hashlib.sha256(body[:35000].encode("utf-8")).hexdigest(), headline

def check_target(target, project, previous, session, checked_at):
    url = target["source_url"]
    host = target["allowed_host"]
    row = {
        "project_id": target["project_id"], "asset_type": "landed",
        "source_id": target["source_id"], "source_url": url,
        "checked_at": checked_at, "status": "not-checked",
        "last_verified_source_at": previous.get("last_verified_source_at"),
        "content_changed": False, "needs_manual_review": False,
        "candidate_price_records": 0, "price_data_published": False,
        "attempts": [],
    }
    if not permitted(url,host) or url != project.get("official_url"):
        row["status"] = "unapproved-source-identity"
        return row
    fallbacks = target.get("fallback_urls", [])
    if not isinstance(fallbacks, list) or any(not permitted(candidate, host) for candidate in fallbacks):
        row["status"] = "unapproved-fallback"
        return row
    candidates = [url] + [f for f in fallbacks if f != url]
    for i, candidate in enumerate(candidates):
        try:
            # Requests performs normal TLS verification. Never verify=False.
            response = session.get(candidate, headers=HEADERS, timeout=16,
                                   allow_redirects=True, stream=True)
            final = response.url
            if not permitted(final,host):
                row["attempts"].append({"url": candidate, "status": "untrusted-redirect"})
                row["status"] = "redirect-outside-approved-publisher"
                return row
            row["attempts"].append({"url": candidate, "status": "http-response",
                                     "http_status": response.status_code})
            row["http_status"] = response.status_code
            if response.status_code != 200:
                row["status"] = "access-unavailable"
                return row
            raw = response.raw.read(MAX_BYTES + 1, decode_content=True)
            if len(raw) > MAX_BYTES:
                row["status"] = "over-size"
                return row
            html = raw.decode(response.encoding or "utf-8", errors="replace")
            digest, headline = text_fingerprint(
                html, project["name"], target.get("page_type","project-landing"),
                target.get("source_title_hint", ""))
            if not digest:
                row["status"] = "project-headline-not-confirmed"
                return row
            row["status"] = "source-page-reachable"
            row["effective_source_url"] = final
            row["page_headline"] = headline
            row["last_verified_source_at"] = checked_at
            # Compare with previous *same publisher page*. Changing fallback
            # host/path does not constitute a project update.
            prior_digest = previous.get("content_sha256") if (
                previous.get("effective_source_url", previous.get("source_url")) == final) else None
            row["content_sha256"] = digest
            row["content_changed"] = bool(prior_digest and prior_digest != digest)
            row["needs_manual_review"] = row["content_changed"]
            return row
        except requests.exceptions.SSLError:
            row["attempts"].append({"url":candidate,"status":"ssl-error"})
            row["status"]="ssl-error"
        except requests.exceptions.ConnectionError:
            row["attempts"].append({"url":candidate,"status":"connection-error"})
            row["status"]="connection-error"
        except requests.RequestException as exc:
            row["attempts"].append({"url":candidate,"status":"network-error",
                                     "error_class":type(exc).__name__})
            row["status"] = "network-error"
            return row
        # Only an explicitly configured official host fallback is allowed;
        # retrying failed TLS on another hostname is NOT a TLS bypass.
    return row

def run(config, registry, old, session, checked_at):
    projects = {p["id"]:p for p in registry["data"]}
    past = {p["project_id"]:p for p in old.get("projects",[])}
    seen=set()
    results=[]
    for target in config.get("targets",[]):
        pid=target["project_id"]
        if pid in seen or pid not in projects:
            raise ValueError("duplicate-or-unknown-landed-project")
        seen.add(pid)
        if "landed" not in projects[pid].get("segment_ids",[]):
            raise ValueError("wrong-product-scope")
        results.append(check_target(target, projects[pid], past.get(pid,{}), session,checked_at))
    if len(results)<1:
        raise ValueError("missing-source-targets")
    return {
        "schema_version":1,"generated_at":checked_at,
        "collection_mode":"official-source-change-watch-only",
        "projects_monitored":len(results),
        "sources_reachable":sum(x["status"]=="source-page-reachable" for x in results),
        "manual_review_leads":sum(x["needs_manual_review"] for x in results),
        "published_prices":0,
        "methodology":"A source availability/content monitor, NOT a price collector. No inferred land price, developer ASP, transaction count or market launch.",
        "projects":results,
    }

def main():
    config=load(CONFIG)
    registry=load(PROJECTS)
    prior=load(STATE,{"projects":[]})
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    results=run(config,registry,prior,requests.Session(),now)
    save(STATE,results)
    print(f"Landed source watch: {results['sources_reachable']}/{results['projects_monitored']} reachable; {results['manual_review_leads']} changes; 0 prices published")

if __name__=="__main__":
    main()
