"""Find an explicit publication date; do not replace it with the HTTP fetch date."""
from __future__ import annotations
from datetime import date, datetime
import re
from bs4 import BeautifulSoup

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def extract_publication_date(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    for attr, key in (
        ("property", "article:published_time"),
        ("name", "datePublished"),
        ("itemprop", "datePublished"),
        ("property", "article:published"),
    ):
        node = soup.find("meta", attrs={attr: key})
        if node:
            raw = node.get("content", "").strip()
            try:
                d = date.fromisoformat(raw[:10])
                return {"date": d.isoformat(), "method": "publication-meta", "evidence": raw}
            except ValueError:
                continue
    node = soup.find("time", datetime=True)
    if node:
        raw = node.get("datetime", "").strip()
        try:
            d = date.fromisoformat(raw[:10])
            return {"date": d.isoformat(), "method": "time-element", "evidence": raw}
        except ValueError:
            pass
    h1 = soup.find("h1")
    body = soup.body or soup
    text = body.get_text(" ", strip=True)
    heading = h1.get_text(" ", strip=True) if h1 else ""
    if heading:
        pos = text.find(heading)
        if pos >= 0:
            text = text[pos + len(heading):pos + len(heading) + 800]
    for m in re.finditer(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+([0-3]?\d),?\s+(20\d{2})\b",
        text, re.I,
    ):
        try:
            d = date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
            return {"date": d.isoformat(), "method": "heading-adjacent-date", "evidence": m.group(0)}
        except ValueError:
            pass
    return {"date": None, "method": "missing", "evidence": None}
