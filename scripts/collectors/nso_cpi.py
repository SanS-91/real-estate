from __future__ import annotations
import re
from bs4 import BeautifulSoup

SOURCE_ID = "nso-vietnam"


def _pct(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.I|re.S)
    return float(m.group(1).replace(",", ".")) if m else None


def parse_nso_cpi(html: str, source_url: str, fetched_at: str):
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)
    period_m = re.search(r"Kỳ tham chiếu:\s*(\d{1,2})/(\d{4})", text, re.I)
    pub_m = re.search(r"Ngày đăng:\s*(\d{1,2})/(\d{1,2})/(\d{4})", text, re.I)
    if not period_m:
        # Fallback to headline/body wording such as tháng 9/2026
        period_m = re.search(r"tháng\s+(\d{1,2})/(\d{4})", text, re.I)
    period = f"{period_m.group(2)}-{int(period_m.group(1)):02d}" if period_m else None
    published_at = f"{pub_m.group(3)}-{int(pub_m.group(2)):02d}-{int(pub_m.group(1)):02d}" if pub_m else None

    mom = _pct(r"CPI\)?\s*tháng[^.]{0,100}?tăng\s+([\d,]+)%\s+so\s+với\s+tháng\s+trước", text)
    yoy = _pct(r"CPI\)?\s*tháng[^.]{0,180}?tăng\s+[\d,]+%\s+so\s+với\s+tháng\s+trước;[^.]{0,160}?tăng\s+([\d,]+)%\s+so\s+với\s+cùng\s+kỳ", text)
    if yoy is None:
        yoy = _pct(r"So\s+với\s+cùng\s+kỳ\s+năm\s+trước,\s*CPI[^.]{0,80}?tăng\s+([\d,]+)%", text)
    core_yoy = _pct(r"lạm\s+phát\s+cơ\s+bản[^.]{0,100}?tăng\s+[\d,]+%\s+so\s+với\s+tháng\s+trước\s+và\s+tăng\s+([\d,]+)%\s+so\s+với\s+cùng\s+kỳ", text)

    out=[]
    for indicator, value in [("cpi-mom",mom),("cpi-yoy",yoy),("core-cpi-yoy",core_yoy)]:
        if value is None: continue
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
    """Return the newest CPI detail URL from NSO CPI listing page."""
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, "lxml")
    candidates = []
    for a in soup.find_all("a", href=True):
        txt = " ".join(a.stripped_strings)
        href = a.get("href")
        if not href:
            continue
        if re.search(r"chỉ\s+số\s+giá\s+tiêu\s+dùng|CPI", txt, re.I):
            if "/202" in href or "chi-so-gia-tieu-dung" in href:
                candidates.append(urljoin(landing_url, href))
    return candidates[0] if candidates else None
