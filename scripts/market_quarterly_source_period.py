"""Detect publisher-authored reporting quarter on rolling Cushman residential MarketBeat.

The landing page URL is reused for each quarter. Never use crawl time,
configured quarter or adjacent comparison quarters as a publication period.
Two independent section anchors must agree before staging quarterly metrics.
"""
from __future__ import annotations

import re
from bs4 import BeautifulSoup

QUARTER = re.compile(r"\bQ([1-4])\s*[/\- ]?\s*(20\d{2})\b", re.I)


def source_quarter(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    # Require a reporting-period reference in BOTH new-supply introductions.
    # QoQ historical comparison dates elsewhere cannot establish the period.
    patterns = {
        "apartment": re.compile(
            r"new supply officially launched in\s+(Q[1-4]\s*[/\- ]?\s*20\d{2})", re.I),
        "landed": re.compile(
            r"(?:in\s+)(Q[1-4]\s*[/\- ]?\s*20\d{2})\s*,?\s*the primary market witnessed", re.I),
    }
    evidence = {}
    for segment, pattern in patterns.items():
        matches = pattern.findall(text)
        normalized = set()
        for phrase in matches:
            period = QUARTER.fullmatch(phrase)
            if period:
                normalized.add(f"{period.group(2)}-Q{period.group(1)}")
        if len(normalized) != 1:
            return {"period": None, "status": "missing-or-ambiguous-"+segment,
                    "evidence": evidence}
        evidence[segment] = next(iter(normalized))
    if evidence["apartment"] != evidence["landed"]:
        return {"period": None, "status": "apartment-landed-period-conflict",
                "evidence": evidence}
    return {"period": evidence["apartment"], "status": "two-segment-agreement",
            "evidence": evidence}
