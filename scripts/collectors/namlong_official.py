from __future__ import annotations

import re
from bs4 import BeautifulSoup

PROJECT_PATTERNS={
    "waterpoint": re.compile(r"\bWaterpoint\b",re.I),
    "mizuki-park": re.compile(r"\bMizuki Park\b",re.I),
    "izumi-city": re.compile(r"\bIzumi City\b",re.I),
    "akari-city": re.compile(r"\bAkari City\b",re.I),
}

def parse_article(html: str, source_url: str, fetched_at: str):
    """Read the article only, excluding global navigation and related-news cards.

    The article publication date must be visible near the article heading, or in
    publication metadata. No guessed dates or page-fetch timestamps are used.
    """
    from datetime import date
    soup = BeautifulSoup(html, "lxml")
    heading = soup.find("h1")
    if not heading:
        raise ValueError("Missing article heading")
    title = heading.get_text(" ", strip=True)
    if not title:
        raise ValueError("Empty article heading")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    page_text = " ".join(soup.stripped_strings)
    pivot = page_text.find(title)
    if pivot < 0:
        raise ValueError("Article heading not in visible page text")
    # Look only in the immediate pre-heading area for an explicit date.
    before = page_text[max(0, pivot - 180):pivot]
    date_string = None
    dates = re.findall(r"\b([0-3]?\d)[/-]([01]?\d)[/-](20\d{2})\b", before)
    if dates:
        day, month, year = dates[-1]
        try:
            date_string = date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            pass

    if date_string is None:
        for attr, key in (("property", "article:published_time"), ("name", "datePublished"), ("itemprop", "datePublished")):
            meta = soup.find("meta", attrs={attr: key})
            if meta:
                raw = meta.get("content", "")
                try:
                    date_string = date.fromisoformat(raw[:10]).isoformat()
                except ValueError:
                    continue
                break

    text = page_text[pivot + len(title):]
    for separator in ("Tin tức khác", "THÔNG TIN LIÊN HỆ", "Những tìm kiếm nổi bật"):
        cut = text.find(separator)
        if cut >= 0:
            text = text[:cut]
    text = text[:20000]
    project_ids = [pid for pid, pat in PROJECT_PATTERNS.items() if pat.search(text)]
    tags = []
    for tag, pat in (
        ("launch", r"mở bán|khởi động kinh doanh|ra mắt|giới thiệu phân khu"),
        ("sales", r"hấp thụ|được thị trường đón nhận|sold|bán"),
        ("handover", r"bàn giao|nhận sổ hồng|handover"),
        ("project-update", r"phân khu|dự án|khu đô thị"),
    ):
        if re.search(pat, text, re.I):
            tags.append(tag)

    facts = []
    m_units = re.search(r"(?:toàn bộ\s+)?(?:hơn\s+)?([\d.,]+)\s+sản phẩm[^.]{0,100}?(?:tỷ lệ hấp thụ\s*)?100%", text, re.I)
    if m_units:
        facts.append({"type": "developer-stated-sales", "units": int(re.sub(r"\D", "", m_units.group(1))), "absorption_rate": 1.0})
    m_cert = re.search(r"(\d{1,3})%\s+hộ\s+đã\s+nhận\s+sổ\s+hồng", text, re.I)
    if m_cert:
        facts.append({"type": "certificate-progress", "household_pct": int(m_cert.group(1)) / 100})

    return {
        "title": title,
        "published_date": date_string,
        "project_ids": project_ids,
        "tags": tags,
        "facts": facts,
        "source_url": source_url,
        "fetched_at": fetched_at,
    }
