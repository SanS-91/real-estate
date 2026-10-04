from __future__ import annotations
import re
from bs4 import BeautifulSoup

SOURCE_ID = "vietcap-research"


def _published_date(soup: BeautifulSoup, text: str):
    for attr, key in [("property", "article:published_time"), ("name", "date"), ("name", "publish-date")]:
        tag = soup.find("meta", attrs={attr: key})
        if tag and tag.get("content"):
            m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", tag.get("content"))
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    t = soup.find("time")
    if t:
        raw = t.get("datetime") or t.get_text(" ", strip=True)
        m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", raw or "")
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    d = re.search(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})", text, re.I)
    months = {m.lower(): i for i, m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], 1)}
    return f"{d.group(3)}-{months[d.group(2).lower()]:02d}-{int(d.group(1)):02d}" if d else None


def parse_vietcap_macro(html: str, source_url: str, fetched_at: str):
    soup = BeautifulSoup(html, "lxml")
    title = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "Vietcap macro research"
    text = " ".join(soup.stripped_strings)
    pub = _published_date(soup, text)
    facts = []
    for pat, metric, unit in [
        (r"CPI[^.]{0,100}?rose\s+([\d.]+)%\s+YoY", "cpi-yoy", "percent"),
        (r"USD/VND[^.]{0,80}?closed\s+at\s+([\d,]+)", "usd-vnd-market-close", "vnd-per-usd"),
        (r"GDP[^.]{0,100}?(?:expanded|growth(?:\s+reached)?)\s+([\d.]+)%\s+YoY", "gdp-yoy", "percent"),
    ]:
        m = re.search(pat, text, re.I)
        if m:
            facts.append({"metric": metric, "value": float(m.group(1).replace(',', '')), "unit": unit})
    return {
        "source_id": SOURCE_ID,
        "title": title,
        "published_at": pub,
        "source_url": source_url,
        "fetched_at": fetched_at,
        "evidence_status": "reported",
        "related_indicator_ids": [f["metric"] for f in facts],
        "facts": facts,
        "summary": "Research evidence only; values/forecasts are preserved with source context and do not overwrite official actual series.",
    }


def discover_vietcap_macro_url(html: str, landing_url: str):
    from urllib.parse import urljoin, urlparse

    soup = BeautifulSoup(html, "lxml")
    excluded = {
        "/en/research-center", "/en/research-center/macroeconomics",
        "/en/research-center/strategy", "/en/research-center/company-research",
        "/en/research-center/sector-reports", "/en/research-center/market-commentary",
        "/en/research-center/fixed-income",
    }
    ranked = []
    for idx, a in enumerate(soup.find_all("a", href=True)):
        href = (a.get("href") or "").strip()
        txt = " ".join(a.stripped_strings)
        if not href:
            continue
        url = urljoin(landing_url, href)
        path = urlparse(url).path.rstrip("/")
        if path in excluded or not path.startswith("/en/research-center/"):
            continue
        tail = path[len("/en/research-center/"):]
        if not tail or "/" in tail:
            continue
        score = 10
        if re.search(r"macro|GDP|CPI|inflation|exchange|USD/VND|econom", txt, re.I):
            score += 40
        if re.search(r"macro|gdp|cpi|inflation|exchange|usd-vnd|econom", tail, re.I):
            score += 30
        score += max(0, 10 - idx)
        ranked.append((score, url))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]
