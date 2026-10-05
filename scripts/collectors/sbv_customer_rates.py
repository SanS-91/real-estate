from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

SOURCE_ID = "sbv-vietnam"


def _num(raw: str | None):
    if raw is None:
        return None
    raw = raw.strip().replace(" ", "")
    if "," in raw and "." in raw:
        # Vietnamese thousands/decimal convention is uncommon for these rates;
        # prefer comma as decimal separator when both appear in copied text.
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", ".")
    return float(raw)


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or " ").strip()


def _period_from_text(text: str):
    # Official bulletin title normally contains THÁNG M/YYYY.
    m = re.search(r"TH[ÁA]NG\s+(\d{1,2})\s*/\s*(20\d{2})", text, re.I)
    if not m:
        m = re.search(r"tháng\s+(\d{1,2})\s*(?:năm\s*)?(20\d{2})", text, re.I)
    if not m:
        return None
    return f"{m.group(2)}-{int(m.group(1)):02d}"


def _range(pattern: str, text: str):
    m = re.search(pattern, text, re.I | re.S)
    if not m:
        return None
    return _num(m.group(1)), _num(m.group(2))


def parse_sbv_customer_rates(text_or_html: str, source_url: str, fetched_at: str):
    """Parse selected customer-rate ranges from the official SBV monthly bulletin.

    The SBV bulletin publishes ranges, not a single scalar '12M average'. To avoid
    silently changing methodology, the collector stores lower/upper bounds as
    separate canonical candidate indicators. Frontend range composition is a later
    phase and the existing demo scalar indicators are intentionally untouched here.
    """
    soup = BeautifulSoup(text_or_html, "lxml")
    text = _compact(" ".join(soup.stripped_strings) if soup.find() else text_or_html)
    period = _period_from_text(text)
    if not period:
        return []

    deposit_6_12 = _range(
        r"([\d.,]+)\s*[-–—]\s*([\d.,]+)\s*%\s*/?\s*năm[^.;]{0,100}?"
        r"tiền\s+gửi\s+có\s+kỳ\s+hạn\s+từ\s+6\s+tháng\s+đến\s+12\s+tháng",
        text,
    )
    if not deposit_6_12:
        deposit_6_12 = _range(
            r"tiền\s+gửi[^.;]{0,900}?kỳ\s+hạn\s+từ\s+6\s+tháng\s+đến\s+12\s+tháng"
            r"[^.;]{0,180}?(?:ở\s+mức\s*)?([\d.,]+)\s*[-–—]\s*([\d.,]+)\s*%",
            text,
        )
    lending_avg = _range(
        r"lãi\s+suất\s+cho\s+vay\s+bình\s+quân[^.;]{0,450}?"
        r"(?:ở\s+mức|mức)\s*([\d.,]+)\s*[-–—]\s*([\d.,]+)\s*%",
        text,
    )
    priority_m = re.search(
        r"lãi\s+suất\s+cho\s+vay\s+ngắn\s+hạn\s+bình\s+quân\s+bằng\s+VND"
        r"[^.;]{0,350}?lĩnh\s+vực\s+ưu\s+tiên[^.;]{0,120}?(?:khoảng|ở\s+mức)\s*([\d.,]+)\s*%",
        text,
        re.I | re.S,
    )

    out = []
    common = {
        "period": period,
        "period_type": "month",
        "unit": "percent-per-year",
        "source_id": SOURCE_ID,
        "source_url": source_url,
        "fetched_at": fetched_at,
        "evidence_status": "verified",
    }
    if deposit_6_12:
        lo, hi = deposit_6_12
        out.extend([
            {
                **common,
                "indicator_id": "deposit-rate-vnd-6-12m-low",
                "value": lo,
                "methodology_note": "Official SBV monthly customer-rate bulletin; lower bound of the average VND deposit-rate range for maturities from 6 to 12 months, new and existing deposits, state-owned and joint-stock commercial banks as reported.",
            },
            {
                **common,
                "indicator_id": "deposit-rate-vnd-6-12m-high",
                "value": hi,
                "methodology_note": "Official SBV monthly customer-rate bulletin; upper bound of the average VND deposit-rate range for maturities from 6 to 12 months, new and existing deposits, state-owned and joint-stock commercial banks as reported.",
            },
        ])
    if lending_avg:
        lo, hi = lending_avg
        out.extend([
            {
                **common,
                "indicator_id": "lending-rate-vnd-average-low",
                "value": lo,
                "methodology_note": "Official SBV monthly customer-rate bulletin; lower bound of the average VND lending-rate range for new and existing outstanding loans of state-owned and joint-stock commercial banks as reported.",
            },
            {
                **common,
                "indicator_id": "lending-rate-vnd-average-high",
                "value": hi,
                "methodology_note": "Official SBV monthly customer-rate bulletin; upper bound of the average VND lending-rate range for new and existing outstanding loans of state-owned and joint-stock commercial banks as reported.",
            },
        ])
    if priority_m:
        out.append({
            **common,
            "indicator_id": "priority-short-term-lending-rate-vnd",
            "value": _num(priority_m.group(1)),
            "methodology_note": "Official SBV monthly customer-rate bulletin; average short-term VND lending rate for priority sectors as reported.",
        })
    return out


def _month_key(text: str):
    m = re.search(r"tháng\s+(\d{1,2})\s*/\s*(20\d{2})", text, re.I)
    if not m:
        m = re.search(r"tháng\s+(\d{1,2})\s*(?:năm\s*)?(20\d{2})", text, re.I)
    if not m:
        return 0
    return int(m.group(2)) * 100 + int(m.group(1))


def discover_sbv_customer_rates_url(html: str, landing_url: str):
    """Select the newest SBV customer-interest-rate bulletin detail page."""
    soup = BeautifulSoup(html, "lxml")
    ranked = []
    for idx, a in enumerate(soup.find_all("a", href=True)):
        title = _compact(" ".join(a.stripped_strings))
        if not title:
            continue
        if not re.search(r"diễn\s+biến\s+lãi\s+suất", title, re.I):
            continue
        if not re.search(r"tổ\s+chức\s+tín\s+dụng|các\s+tổ\s+chức\s+tín\s+dụng", title, re.I):
            continue
        href = (a.get("href") or "").strip()
        if not href:
            continue
        url = urljoin(landing_url, href)
        ranked.append((_month_key(title), -idx, url))
    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][2]


def discover_sbv_customer_rates_attachment(html: str, detail_url: str):
    """Find the attached SBV PDF carrying the monthly rate table/text."""
    soup = BeautifulSoup(html, "lxml")
    candidates = []
    for idx, a in enumerate(soup.find_all("a", href=True)):
        href = (a.get("href") or "").strip()
        label = _compact(" ".join(a.stripped_strings))
        if not href:
            continue
        url = urljoin(detail_url, href)
        path = urlparse(url).path.lower()
        is_pdf = path.endswith(".pdf") or ".pdf/" in path or "download=true" in url.lower()
        if not is_pdf:
            continue
        score = 0
        hay = f"{label} {href}".lower()
        if "lai" in hay and "suat" in hay:
            score += 20
        if "/documents/" in path:
            score += 10
        candidates.append((score, -idx, url))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]
