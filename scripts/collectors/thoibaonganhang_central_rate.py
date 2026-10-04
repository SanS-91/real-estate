from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

SOURCE_ID = "banking-times-vn"


def _published_date(soup: BeautifulSoup, text: str):
    for attrs in [
        {"property": "article:published_time"},
        {"name": "date"},
        {"name": "publish-date"},
    ]:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", tag["content"])
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # Common current shape: "09:26 | 02/10/2026"
    m = re.search(r"(?:\d{1,2}:\d{2}\s*[|\-]\s*)?(\d{1,2})/(\d{1,2})/(20\d{2})", text)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def parse_thoibaonganhang_central_rate(html: str, source_url: str, fetched_at: str):
    """Parse Thời Báo Ngân Hàng reporting of the SBV central USD/VND rate.

    This is corroborating evidence, not a direct SBV canonical record.
    """
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)

    rate = None
    patterns = [
        r"(?:NHNN|Ngân\s+hàng\s+Nhà\s+nước)[^.]{0,120}?tỷ\s+giá\s+trung\s+tâm[^.]{0,120}?(?:mức|là|ở\s+mức)\s+([\d.]+)\s*(?:đồng|VND)(?:/USD)?",
        r"tỷ\s+giá\s+trung\s+tâm[^.]{0,140}?(?:mức|là|ở\s+mức)\s+([\d.]+)\s*(?:đồng|VND)(?:/USD)?",
        r"tỷ\s+giá\s+trung\s+tâm[^.]{0,80}?([\d.]{5,})\s*(?:đồng|VND)(?:/USD)?",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            rate = float(re.sub(r"[^0-9]", "", m.group(1)))
            break

    if rate is None or rate < 10_000:
        return []

    published_at = _published_date(soup, text)
    # Central rate is a daily official reference rate; article date is the business data date.
    data_date = published_at

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
        "methodology_note": "Thời Báo Ngân Hàng report citing the State Bank of Vietnam central rate. Independent corroborating evidence; not a substitute for direct SBV verification.",
    }]


def discover_thoibaonganhang_central_rate_url(html: str, landing_url: str):
    soup = BeautifulSoup(html, "lxml")
    ranked = []
    landing_path = urlparse(landing_url).path.rstrip("/").lower()

    for idx, a in enumerate(soup.find_all("a", href=True)):
        txt = " ".join(a.stripped_strings)
        href = (a.get("href") or "").strip()
        if not href:
            continue
        if not re.search(r"tỷ\s+giá\s+trung\s+tâm|NHNN[^\n]{0,80}?tỷ\s+giá", txt, re.I):
            continue
        url = urljoin(landing_url, href)
        path = urlparse(url).path.rstrip("/").lower()
        if not path or path == landing_path:
            continue
        score = 100 - min(idx, 80)
        if re.search(r"sáng|hôm\s+nay|\d{1,2}/\d{1,2}", txt, re.I):
            score += 20
        if "ty-gia-trung-tam" in path or "nhnn-niem-yet" in path:
            score += 20
        ranked.append((score, url))

    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]
