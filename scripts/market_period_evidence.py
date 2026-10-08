"""Extract a single source-visible reporting quarter; ambiguity is a review gate."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup

def extract_period_evidence(html: str, url: str = "") -> dict:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    parts = []
    for node in [soup.title, soup.find("h1"), soup.find("meta", attrs={"name": "description"})]:
        if node:
            value = node.get("content", "") if node.name == "meta" else node.get_text(" ", strip=True)
            if value:
                parts.append(value)
    text = " ".join(parts)
    matches = []
    patterns = [
        r"\bQ([1-4])\s*[/\- ]?\s*(20\d{2})\b",
        r"\b(?:quarter|quý)\s*([1-4])\s*[/\- ]?\s*(20\d{2})\b",
        r"\b(20\d{2})\s*[/\- ]?\s*Q([1-4])\b",
    ]
    for idx, pattern in enumerate(patterns):
        for match in re.finditer(pattern, text, re.I):
            year, quarter = (match.group(2), match.group(1)) if idx < 2 else (match.group(1), match.group(2))
            matches.append((f"{year}-Q{quarter}", match.group(0)))
    periods = sorted(set(p for p, _ in matches))
    return {
        "period": periods[0] if len(periods) == 1 else None,
        "evidence": [x[1] for x in matches][:8],
        "status": "single-period" if len(periods) == 1 else ("ambiguous" if periods else "missing"),
        "source_url": url,
    }
