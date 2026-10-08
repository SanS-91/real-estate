"""Fail-closed auto-promotion of independently dated official Nam Long news.

Only official article URLs *discovered from the publisher's own index* are eligible.
Quarterly market metrics and other articles continue through manual review.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "data/mock/articles/articles.json"
CANDIDATES = ROOT / "data/candidate/market/articles.json"
COLLECTOR_REPORT = ROOT / "data/candidate/market/market-source-candidate-report.json"
REPORT = ROOT / "data/candidate/market/market-verified-auto-promotion-report.json"
SOURCES = ROOT / "data/mock/core/sources.json"
PROJECTS = ROOT / "data/mock/market/projects.json"

OFFICIAL_HOST = "namlongvn.com"
INDEX_URL = "https://www.namlongvn.com/tin-tuc/"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical(url):
    p = urlsplit(url or "")
    host = (p.hostname or "").lower().removeprefix("www.")
    segments = [x for x in p.path.strip("/").split("/") if x]
    if p.scheme != "https" or host != OFFICIAL_HOST or len(segments) != 2:
        return None
    if segments[0] != "tin-tuc" or not segments[1] or p.query or p.fragment:
        return None
    return f"https://www.namlongvn.com/tin-tuc/{segments[1]}/"


def assess(row, source_ids, project_ids, today):
    url = canonical(row.get("url"))
    proof = row.get("source_verification") or {}
    if not url:
        return "non-official-or-invalid-article-url"
    if proof.get("discovery_url") != INDEX_URL or not proof.get("publication_date_verified"):
        return "missing-official-index-and-date-evidence"
    if canonical(proof.get("article_page")) != url:
        return "source-url-evidence-mismatch"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    if row.get("id") != "article-market-nam-long-discovered-" + digest:
        return "article-identity-mismatch"
    if row.get("source_id") != "nam-long-official" or row.get("source_id") not in source_ids:
        return "unapproved-source"
    if row.get("category") != "market" or row.get("content_type") != "developer-update":
        return "unexpected-category"
    if not row.get("title") or len(row["title"].strip()) < 20:
        return "missing-title"
    if not row.get("summary") or len(row["summary"].strip()) < 30:
        return "missing-source-summary"
    if set(row.get("project_ids") or []) - project_ids:
        return "unknown-project-reference"
    try:
        published = datetime.fromisoformat(row["published_at"])
        if published.tzinfo is None or not (2024 <= published.year <= today.year):
            return "invalid-publication-timestamp"
        if published.date() > today.date():
            return "future-publication"
    except (TypeError, ValueError, KeyError):
        return "invalid-publication-timestamp"
    return None


def prepare_updates(existing, candidates, source_ids, project_ids, today):
    existing_urls = {canonical(x.get("url")) for x in existing}
    seen = set()
    accepted = []
    decisions = []
    for row in candidates:
        url = canonical(row.get("url"))
        if url is None:
            # Other candidate source types are deliberately never auto-promoted.
            decisions.append({"id": row.get("id"), "decision": "manual-review", "reason": "not-approved-official-news"})
            continue
        reason = assess(row, source_ids, project_ids, today)
        if reason:
            decisions.append({"id": row.get("id"), "decision": "manual-review", "reason": reason})
            continue
        if url in seen:
            decisions.append({"id": row.get("id"), "decision": "manual-review", "reason": "duplicate-candidate"})
            continue
        seen.add(url)
        if url in existing_urls:
            decisions.append({"id": row["id"], "decision": "unchanged", "reason": "source-url-already-published"})
            continue
        accepted.append(copy.deepcopy(row))
        decisions.append({"id": row["id"], "decision": "new", "reason": "verified-official-discovered-article"})
    return accepted, decisions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["preview", "promote"], default="preview")
    args = ap.parse_args()
    existing_payload = read(ARTICLES)
    candidates_payload = read(CANDIDATES)
    collector_report = read(COLLECTOR_REPORT)
    sources = {v["id"] for v in read(SOURCES).get("data", [])}
    projects = {v["id"] for v in read(PROJECTS).get("data", [])}
    if not candidates_payload.get("candidate_only"):
        raise SystemExit("Refuse publication: candidate-only source flag is absent")
    if candidates_payload.get("record_count") != len(candidates_payload.get("data", [])):
        raise SystemExit("Refuse publication: candidate record count mismatch")
    discovered = collector_report.get("discovery") or []
    if not any(x.get("index") == INDEX_URL and x.get("status") == "discovered" for x in discovered):
        raise SystemExit("Refuse publication: official news-index discovery not verified")
    additions, decisions = prepare_updates(
        existing_payload.get("data", []),
        candidates_payload.get("data", []),
        sources,
        projects,
        datetime.now(timezone.utc),
    )
    result = {
        "schema_version": 1, "mode": args.mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_written": False,
        "eligible_new_articles": len(additions),
        "manual_review": sum(x["decision"] == "manual-review" for x in decisions),
        "unchanged": sum(x["decision"] == "unchanged" for x in decisions),
        "decisions": decisions,
    }
    if args.mode == "promote" and additions:
        payload = copy.deepcopy(existing_payload)
        payload["data"] = sorted(
            payload.get("data", []) + additions,
            key=lambda x: (x.get("published_at") or "", x.get("id") or ""),
            reverse=True,
        )
        payload["record_count"] = len(payload["data"])
        payload["generated_at"] = result["generated_at"]
        payload["build_id"] = "market-verified-official-news-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        write(ARTICLES, payload)
        result["production_written"] = True
        result["added_articles"] = len(additions)
        result["final_article_count"] = len(payload["data"])
    write(REPORT, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
