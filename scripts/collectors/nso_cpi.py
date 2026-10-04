from __future__ import annotations
import re
from bs4 import BeautifulSoup

SOURCE_ID = "nso-vietnam"


def _pct(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.I | re.S)
    return float(m.group(1).replace(",", ".")) if m else None


def parse_nso_cpi(html: str, source_url: str, fetched_at: str):
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)

    period_m = re.search(r"Kỳ\s+tham\s+chiếu\s*:\s*(?:Tháng\s*)?(\d{1,2})/(\d{4})", text, re.I)
    if not period_m:
        period_m = re.search(r"CPI[^.]{0,60}?tháng\s+(\d{1,2})/(\d{4})", text, re.I)
    if not period_m:
        period_m = re.search(r"tháng\s+(\d{1,2})/(\d{4})", text, re.I)
    period = f"{period_m.group(2)}-{int(period_m.group(1)):02d}" if period_m else None

    pub_m = re.search(r"Ngày\s+đăng\s*:\s*(\d{1,2})/(\d{1,2})/(\d{4})", text, re.I)
    published_at = f"{pub_m.group(3)}-{int(pub_m.group(2)):02d}-{int(pub_m.group(1)):02d}" if pub_m else None

    mom = _pct(
        r"(?:Chỉ\s+số\s+giá\s+tiêu\s+dùng\s*\(CPI\)|CPI)[^.]{0,140}?tháng\s+(?:\d{1,2}/\d{4}|[^\s,;.]+)[^.]{0,140}?tăng\s+([\d,]+)%\s+so\s+với\s+tháng\s+trước",
        text,
    )
    if mom is None:
        mom = _pct(r"So\s+với\s+tháng\s+trước,\s*CPI[^.]{0,100}?tăng\s+([\d,]+)%", text)

    yoy = _pct(
        r"(?:Chỉ\s+số\s+giá\s+tiêu\s+dùng\s*\(CPI\)|CPI)[^.]{0,400}?tăng\s+([\d,]+)%\s+so\s+với\s+cùng\s+kỳ",
        text,
    )
    if yoy is None:
        yoy = _pct(r"So\s+với\s+cùng\s+kỳ\s+năm\s+trước,\s*CPI[^.]{0,120}?tăng\s+([\d,]+)%", text)

    core_yoy = _pct(
        r"Lạm\s+phát\s+cơ\s+bản[^.]{0,120}?tháng\s+\d{1,2}/\d{4}[^.]{0,180}?tăng\s+[\d,]+%\s+so\s+với\s+tháng\s+trước\s+và\s+tăng\s+([\d,]+)%\s+so\s+với\s+cùng\s+kỳ",
        text,
    )
    if core_yoy is None:
        core_yoy = _pct(r"lạm\s+phát\s+cơ\s+bản[^.]{0,160}?tăng\s+([\d,]+)%\s+so\s+với\s+cùng\s+kỳ", text)

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
            "evidence_status": "verified",
            "methodology_note": "Official NSO statistical release; percentage change exactly as stated in release."
        })
    return out


def discover_nso_cpi_url(html: str, landing_url: str):
    """Return the newest CPI detail URL from the NSO CPI listing page."""
    from urllib.parse import urljoin, urlparse

    soup = BeautifulSoup(html, "lxml")
    ranked = []
    for idx, a in enumerate(soup.find_all("a", href=True)):
        txt = " ".join(a.stripped_strings)
        href = (a.get("href") or "").strip()
        if not href:
            continue
        if not re.search(r"chỉ\s+số\s+giá\s+tiêu\s+dùng|CPI|tình\s+hình\s+giá", txt, re.I):
            continue
        url = urljoin(landing_url, href)
        path = urlparse(url).path.lower()
        if path.rstrip("/") in {"/cpi-vi", "/cpi"}:
            continue
        score = 0
        if "/du-lieu-va-so-lieu-thong-ke/" in path:
            score += 40
        if "/tin-tuc-thong-ke/" in path:
            score += 35
        if re.search(r"/20\d{2}/\d{1,2}/", path):
            score += 30
        if "ngày đăng" in txt.lower():
            score += 10
        score += max(0, 20 - idx)
        ranked.append((score, url))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]
