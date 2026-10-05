from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

SOURCE_ID = "nso-vietnam"


def _pct(raw: str | None):
    if raw is None:
        return None
    return float(raw.replace(".", "").replace(",", ".")) if "," in raw else float(raw)


def _published_at(soup: BeautifulSoup, text: str):
    # Prefer machine-readable publication metadata when available.
    for attr, value in [
        (("meta", {"property": "article:published_time"}), "content"),
        (("meta", {"name": "date"}), "content"),
        (("meta", {"itemprop": "datePublished"}), "content"),
    ]:
        node = soup.find(attr[0], attrs=attr[1])
        if node and node.get(value):
            m = re.match(r"(20\d{2}-\d{2}-\d{2})", node.get(value).strip())
            if m:
                return m.group(1)

    # Some NSO pages expose schema.org JSON-LD.
    for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(node.string or "{}")
        except Exception:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            value = item.get("datePublished")
            if isinstance(value, str):
                m = re.match(r"(20\d{2}-\d{2}-\d{2})", value.strip())
                if m:
                    return m.group(1)

    m = re.search(r"Ngày\s+đăng\s*:\s*(\d{1,2})/(\d{1,2})/(20\d{2})", text, re.I)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def parse_nso_banking_activity(html: str, source_url: str, fetched_at: str):
    """Parse YTD credit growth and credit-institution funding growth from an NSO release.

    The NSO socio-economic release normally states both observations in the same banking
    paragraph, for example: "Tính đến thời điểm 28/9/2026, huy động vốn ... tăng 9,78% ...;
    tăng trưởng tín dụng ... đạt 10,89%". We preserve the exact as-of date while using the
    containing month as the period so the observations integrate with monthly macro series.
    """
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)

    # Isolate the banking sentence/paragraph first so similarly worded percentages elsewhere
    # in the socio-economic report cannot be mistaken for these indicators.
    banking_m = re.search(
        r"(Tính\s+đến\s+(?:thời\s+điểm|ngày)\s+\d{1,2}/\d{1,2}/20\d{2}[^.]{0,900}?"
        r"huy\s+động\s+vốn[^.]{0,900}?tăng\s+trưởng\s+tín\s+dụng[^.]{0,500}?\.)",
        text,
        flags=re.I | re.S,
    )
    segment = banking_m.group(1) if banking_m else text

    date_m = re.search(
        r"Tính\s+đến\s+(?:thời\s+điểm|ngày)\s+(\d{1,2})/(\d{1,2})/(20\d{2})",
        segment,
        re.I,
    )
    data_date = None
    period = None
    if date_m:
        data_date = f"{date_m.group(3)}-{int(date_m.group(2)):02d}-{int(date_m.group(1)):02d}"
        period = f"{date_m.group(3)}-{int(date_m.group(2)):02d}"

    funding_m = re.search(
        r"huy\s+động\s+vốn\s+của\s+các\s+tổ\s+chức\s+tín\s+dụng[^.;]{0,220}?"
        r"tăng\s+([\d.,]+)%",
        segment,
        re.I | re.S,
    )
    credit_m = re.search(
        r"tăng\s+trưởng\s+tín\s+dụng(?:\s+của\s+nền\s+kinh\s+tế)?[^.;]{0,160}?"
        r"(?:đạt|tăng)\s+([\d.,]+)%",
        segment,
        re.I | re.S,
    )

    published_at = _published_at(soup, text)
    out = []
    if funding_m:
        out.append({
            "indicator_id": "bank-funding-growth-ytd",
            "period": period,
            "period_type": "month",
            "data_date": data_date,
            "value": _pct(funding_m.group(1)),
            "unit": "percent",
            "source_id": SOURCE_ID,
            "source_url": source_url,
            "published_at": published_at,
            "fetched_at": fetched_at,
            "evidence_status": "verified",
            "methodology_note": "Official NSO socio-economic release; growth in capital mobilization by credit institutions versus end of prior year, preserving the release's as-of date.",
        })
    if credit_m:
        out.append({
            "indicator_id": "credit-growth-ytd",
            "period": period,
            "period_type": "month",
            "data_date": data_date,
            "value": _pct(credit_m.group(1)),
            "unit": "percent",
            "source_id": SOURCE_ID,
            "source_url": source_url,
            "published_at": published_at,
            "fetched_at": fetched_at,
            "evidence_status": "verified",
            "methodology_note": "Official NSO socio-economic release; economy-wide credit growth YTD as stated in the banking section, preserving the release's as-of date.",
        })
    return out


def discover_nso_banking_activity_url(html: str, landing_url: str):
    """Find the newest NSO socio-economic report likely to contain banking activity data."""
    soup = BeautifulSoup(html, "lxml")
    ranked = []
    for idx, a in enumerate(soup.find_all("a", href=True)):
        title = " ".join(a.stripped_strings)
        href = (a.get("href") or "").strip()
        if not title or not href:
            continue
        normalized = re.sub(r"\s+", " ", title).lower()
        if not (re.search(r"kinh\s*tế", normalized, re.I) and re.search(r"xã\s*hội", normalized, re.I)):
            continue
        if not re.search(r"báo\s+cáo|thông\s+cáo", normalized, re.I):
            continue
        url = urljoin(landing_url, href)
        path = urlparse(url).path.lower()
        if path.rstrip("/") in {"/tin-tuc-thong-ke", "/du-lieu-va-so-lieu-thong-ke", "/bai-top"}:
            continue

        score = 0
        if "/bai-top/" in path:
            score += 45
        if "/du-lieu-va-so-lieu-thong-ke/" in path:
            score += 40
        if "/tin-tuc-thong-ke/" in path:
            score += 35
        date_path = re.search(r"/(20\d{2})/(\d{1,2})/", path)
        if date_path:
            score += 30
        year_month_rank = int(date_path.group(1)) * 100 + int(date_path.group(2)) if date_path else 0
        if re.search(r"quý|tháng|[0-9]+\s+tháng", normalized, re.I):
            score += 12
        # NSO listing pages are reverse chronological; use position only as a small tie-breaker.
        score += max(0, 20 - idx)
        ranked.append((year_month_rank, score, -idx, url))

    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][3]
