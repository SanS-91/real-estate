from __future__ import annotations
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

SOURCE_ID = "vna-vietnamplus"

MONTHS_VI = {
    "một": 1, "hai": 2, "ba": 3, "tư": 4, "bốn": 4, "năm": 5, "sáu": 6,
    "bảy": 7, "tám": 8, "chín": 9, "mười": 10, "mười một": 11, "mười hai": 12,
}


def _num(raw: str | None):
    return float(raw.replace(",", ".")) if raw else None


def _published_date(soup: BeautifulSoup, text: str):
    for attrs in [
        {"property": "article:published_time"}, {"name": "date"}, {"name": "publish-date"},
    ]:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", tag["content"])
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    t = soup.find("time")
    if t:
        raw = t.get("datetime") or t.get_text(" ", strip=True)
        m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", raw or "")
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{1,2})/(\d{1,2})/(20\d{2})", text)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def _period(text: str, published_at: str | None):
    m = re.search(r"CPI\s+tháng\s+(\d{1,2})/(20\d{2})", text, re.I)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    m = re.search(r"(?:CPI|chỉ\s+số\s+giá\s+tiêu\s+dùng)\s+tháng\s+([A-Za-zÀ-ỹ\s]+?)(?:\s+năm)?\s+(20\d{2})", text, re.I)
    if m:
        name = re.sub(r"\s+", " ", m.group(1).strip().lower())
        # Longest month names first.
        for key in sorted(MONTHS_VI, key=len, reverse=True):
            if name.startswith(key):
                return f"{m.group(2)}-{MONTHS_VI[key]:02d}"
    # VNA CPI articles are normally published in the following month. Do not infer period
    # unless the article body/title states it explicitly.
    return None


def parse_vietnamplus_cpi(html: str, source_url: str, fetched_at: str):
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)
    published_at = _published_date(soup, text)
    period = _period(text, published_at)

    mom = None
    for pat in [
        r"CPI\s+tháng[^.]{0,80}?tăng\s+([\d,.]+)%\s+so\s+với\s+tháng\s+(?:trước|8)",
        r"consumer\s+price\s+index\s*\(CPI\)[^.]{0,100}?rose\s+([\d.]+)\s*per\s+cent[^.]{0,40}?from\s+the\s+previous\s+month",
        r"CPI[^.]{0,80}?rose\s+([\d.]+)%\s+in\s+September\s+from\s+the\s+previous\s+month",
    ]:
        m = re.search(pat, text, re.I)
        if m:
            mom = _num(m.group(1)); break

    yoy = None
    for pat in [
        r"CPI\s+tháng[^.]{0,140}?tăng\s+([\d,.]+)%\s+so\s+với\s+cùng\s+kỳ",
        r"September(?:'s)?\s+CPI[^.]{0,100}?up\s+([\d.]+)%\s+year[- ]on[- ]year",
        r"CPI[^.]{0,100}?([\d.]+)%\s+(?:above|higher than)[^.]{0,40}?a\s+year\s+earlier",
    ]:
        m = re.search(pat, text, re.I)
        if m:
            yoy = _num(m.group(1)); break

    core_yoy = None
    for pat in [
        r"lạm\s+phát\s+cơ\s+bản\s+tháng[^.]{0,120}?tăng\s+[\d,.]+%\s+so\s+với\s+tháng\s+trước\s+và\s+tăng\s+([\d,.]+)%\s+so\s+với\s+cùng\s+kỳ",
        r"core\s+inflation[^.]{0,120}?([\d.]+)%\s+year[- ]on[- ]year",
    ]:
        m = re.search(pat, text, re.I)
        if m:
            core_yoy = _num(m.group(1)); break

    out = []
    for indicator, value in [("cpi-mom", mom), ("cpi-yoy", yoy), ("core-cpi-yoy", core_yoy)]:
        if value is None:
            continue
        out.append({
            "indicator_id": indicator,
            "period": period,
            "period_type": "month",
            "data_date": None,
            "value": value,
            "unit": "percent",
            "source_id": SOURCE_ID,
            "source_url": source_url,
            "published_at": published_at,
            "fetched_at": fetched_at,
            "evidence_status": "reported",
            "methodology_note": "VNA/VietnamPlus report citing Vietnam NSO; fallback evidence, not a substitute for direct NSO verification.",
        })
    return out


def discover_vietnamplus_cpi_url(html: str, landing_url: str):
    soup = BeautifulSoup(html, "lxml")
    ranked = []
    for idx, a in enumerate(soup.find_all("a", href=True)):
        txt = " ".join(a.stripped_strings)
        href = (a.get("href") or "").strip()
        if not href or not re.search(r"\bCPI\b|chỉ\s+số\s+giá\s+tiêu\s+dùng|consumer\s+price", txt, re.I):
            continue
        url = urljoin(landing_url, href)
        path = urlparse(url).path.lower()
        if "tag" in path or path.rstrip("/") == urlparse(landing_url).path.rstrip("/").lower():
            continue
        score = 100 - min(idx, 80)
        if re.search(r"tháng|month|september|october|august", txt, re.I): score += 20
        if re.search(r"20\d{2}", txt): score += 10
        ranked.append((score, url))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]
