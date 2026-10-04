from __future__ import annotations
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

SOURCE_ID = "vna-vietnamplus"


def _published_date(soup: BeautifulSoup, text: str):
    for attrs in [{"property": "article:published_time"}, {"name": "date"}, {"name": "publish-date"}]:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", tag["content"])
            if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    months = {m.lower(): i for i, m in enumerate([
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ], 1)}
    m = re.search(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20\d{2})", text, re.I)
    if not m:
        m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20\d{2})", text, re.I)
    if m:
        return f"{m.group(3)}-{months[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{1,2})/(\d{1,2})/(20\d{2})", text)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def parse_vietnamplus_central_rate(html: str, source_url: str, fetched_at: str):
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)
    rate = None
    for pat in [
        r"(?:reference|central)\s+exchange\s+rate[^.]{0,100}?(?:at|to)\s+([\d,]+)\s*VND/USD",
        r"tỷ\s+giá\s+trung\s+tâm[^.]{0,120}?(?:mức|là|ở)\s+([\d.]+)\s*(?:đồng|VND)/?USD",
    ]:
        m = re.search(pat, text, re.I)
        if m:
            rate = float(m.group(1).replace(",", "").replace(".", "")); break
    if rate is None:
        return []
    published_at = _published_date(soup, text)
    data_date = published_at
    # Prefer an explicit article date in URL/text when present.
    m = re.search(r"(?:on\s+)?(?:October|September|August|July|June|May|April|March|February|January|November|December)\s+(\d{1,2})", text, re.I)
    return [{
        "indicator_id": "usd-vnd-central-rate",
        "period": data_date,
        "period_type": "day",
        "data_date": data_date,
        "value": rate,
        "unit": "vnd-per-usd",
        "source_id": SOURCE_ID,
        "source_url": source_url,
        "published_at": published_at,
        "fetched_at": fetched_at,
        "evidence_status": "reported",
        "methodology_note": "VNA/VietnamPlus report citing the State Bank of Vietnam daily reference rate; fallback evidence only.",
    }]


def discover_vietnamplus_central_rate_url(html: str, landing_url: str):
    soup = BeautifulSoup(html, "lxml")
    ranked = []
    for idx, a in enumerate(soup.find_all("a", href=True)):
        txt = " ".join(a.stripped_strings)
        href = (a.get("href") or "").strip()
        if not href or not re.search(r"reference\s+exchange\s+rate|tỷ\s+giá\s+trung\s+tâm", txt, re.I):
            continue
        url = urljoin(landing_url, href)
        path = urlparse(url).path.lower()
        if "tag" in path or path.rstrip("/") == urlparse(landing_url).path.rstrip("/").lower():
            continue
        score = 100 - min(idx, 80)
        if re.search(r"today|october|september|20\d{2}", txt, re.I): score += 20
        ranked.append((score, url))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]
