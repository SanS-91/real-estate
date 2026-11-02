"""Savills official Vietnam market brief: report-aware, fail-closed evidence.

A publisher article is a source candidate, not a quantitative market metric.
Never infer reporting date from crawl time or retain any hardcoded Q2 summary.
"""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from market_period_evidence import extract_period_evidence
from market_publication_evidence import extract_publication_date

REPORT_PATH = re.compile(r"^/research_articles/\\d+/\\d+-\\d+(?:/[^?#]+)?/?$", re.I)


def parse_article(html: str, source_url: str, fetched_at: str):
    link = urlsplit(source_url)
    host = (link.hostname or "").lower()
    if host not in {"www.savills.com.vn", "vn.savills.com.vn", "savills.com.vn"} or not REPORT_PATH.fullmatch(link.path):
        raise ValueError("not-an-official-individual-savills-research-article")
    if link.scheme != "https" or link.query or link.fragment:
        raise ValueError("unexpected-source-url")

    soup = BeautifulSoup(html, "lxml")
    heading = soup.find("h1")
    title = heading.get_text(" ", strip=True) if heading else ""
    if not re.search(r"(?:Viet\\s*Nam|Vietnam|Việt Nam).{0,60}(?:Market Brief|Bất Động Sản).{0,35}Q[1-4]\\s*[/\\- ]\\s*20\\d{2}", title, re.I):
        raise ValueError("not-a-vietnam-quarterly-market-brief")
    period = extract_period_evidence(html, source_url)
    if period["status"] != "single-period":
        raise ValueError("missing-or-ambiguous-reporting-quarter")
    published = extract_publication_date(html)
    if not published["date"]:
        raise ValueError("publication-date-not-visible")
    if date.fromisoformat(published["date"]) > date.today():
        raise ValueError("future-publication-date")

    # A report headline is trustworthy evidence. Do not manufacture an ASP,
    # absorption, sales value, or interpret official eligibility as sales.
    sections = []
    for tag in soup.find_all(["h2", "h3"]):
        label = tag.get_text(" ", strip=True)
        if re.search(r"(?:HCMC|TP\\.?HCM|HỒ CHÍ MINH|HO CHI MINH).{0,28}(?:OVERVIEW|TỔNG QUAN)", label, re.I):
            sections.append(label)
    return {
        "title": title,
        "published_date": published["date"],
        "publication_date_method": published["method"],
        "report_period": period["period"],
        "report_scope": "Vietnam national brief with HCMC and Hanoi sections",
        "summary": "Savills quarterly report; check the original source for each region and metric. No quantified market result is inferred from this page.",
        "tags": ["research", "vietnam", period["period"].lower(), "market-brief"],
        "source_url": source_url,
        "fetched_at": fetched_at,
        "sections_detected": sections,
    }
