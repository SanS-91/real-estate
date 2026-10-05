from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

POLICY_EVENT_TERMS = re.compile(
    r"(?:điều\s+chỉnh|giảm|hạ|tăng|thay\s+đổi)[^\n]{0,80}lãi\s+suất\s+điều\s+hành|"
    r"lãi\s+suất\s+tái\s+cấp\s+vốn|lãi\s+suất\s+tái\s+chiết\s+khấu",
    re.I,
)
AUTHORITY_TERMS = re.compile(r"Ngân\s+hàng\s+Nhà\s+nước|\bNHNN\b", re.I)
DECISION_RE = re.compile(r"\b(\d{2,5}\s*/\s*QĐ\s*-?\s*NHNN)\b", re.I)


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or " ").strip()


def _num(raw: str | None):
    if raw is None:
        return None
    return float(raw.strip().replace(",", "."))


def _iso_date(y: int, m: int, d: int) -> str:
    try:
        return datetime(y, m, d).date().isoformat()
    except Exception:
        return ""


def published_at(soup: BeautifulSoup, text: str):
    for attrs in (
        {"property": "article:published_time"},
        {"name": "date"},
        {"name": "publish-date"},
        {"name": "pubdate"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", tag["content"])
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    for pat in [
        r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b",
        r"\b(\d{1,2})-(\d{1,2})-(20\d{2})\b",
    ]:
        m = re.search(pat, text)
        if m:
            return _iso_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def effective_date(text: str, pub: str | None):
    # Fully-qualified numeric dates first.
    patterns = [
        r"(?:có\s+hiệu\s+lực|hiệu\s+lực)[^.]{0,80}?(\d{1,2})[/-](\d{1,2})[/-](20\d{2})",
        r"(?:áp\s+dụng|thực\s+hiện)[^.]{0,80}?(?:từ\s+ngày\s+)?(\d{1,2})[/-](\d{1,2})[/-](20\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return _iso_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))

    # Vietnamese long-form date.
    m = re.search(
        r"(?:có\s+hiệu\s+lực|hiệu\s+lực)[^.]{0,100}?ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(20\d{2})",
        text,
        re.I,
    )
    if m:
        return _iso_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))

    # Day/month without year: infer year from article publication.
    m = re.search(r"(?:có\s+hiệu\s+lực|hiệu\s+lực)[^.]{0,80}?(\d{1,2})/(\d{1,2})(?!/\d)", text, re.I)
    if m and pub:
        return _iso_date(int(pub[:4]), int(m.group(2)), int(m.group(1)))

    # "hôm nay 19/6/2023" wording used in weekly market recaps.
    m = re.search(r"(?:hôm\s+nay|từ\s+ngày)\s+(\d{1,2})/(\d{1,2})/(20\d{2})", text, re.I)
    if m:
        return _iso_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return pub


def _rate_after_label(text: str, label_pattern: str):
    # Prefer the post-change level after xuống/lên/còn/ở mức.
    patterns = [
        rf"{label_pattern}[^.;]{{0,240}}?(?:xuống|lên|còn|ở\s+mức|mức\s+mới\s+là)\s*(?:mức\s*)?([0-9]+(?:[,.][0-9]+)?)\s*%",
        rf"{label_pattern}[^.;]{{0,180}}?([0-9]+(?:[,.][0-9]+)?)\s*%\s*/?\s*năm",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I | re.S)
        if m:
            return _num(m.group(1))
    return None


def parse_policy_news(html: str, source_url: str, fetched_at: str, source_id: str):
    soup = BeautifulSoup(html, "lxml")
    text = compact(" ".join(soup.stripped_strings))
    pub = published_at(soup, text)
    eff = effective_date(text, pub)

    decision_match = DECISION_RE.search(text)
    decision = None
    if decision_match:
        decision = re.sub(r"\s+", "", decision_match.group(1)).replace("QĐ-", "QĐ-").upper()

    refinancing = _rate_after_label(text, r"lãi\s+suất\s+tái\s+cấp\s+vốn")
    rediscount = _rate_after_label(text, r"lãi\s+suất\s+tái\s+chiết\s+khấu")
    overnight = _rate_after_label(
        text,
        r"lãi\s+suất\s+cho\s+vay\s+qua\s+đêm(?:\s+trong\s+thanh\s+toán\s+điện\s+tử\s+liên\s+ngân\s+hàng)?",
    )

    # A policy event must resolve the complete administered-rate trio. Partial
    # commentary/forecasts are not converted into policy observations.
    if not eff or any(v is None for v in (refinancing, rediscount, overnight)):
        return []

    event_key = decision or f"POLICY-EVENT-{eff}"
    common = {
        "period": eff,
        "period_type": "date",
        "data_date": eff,
        "unit": "percent-per-year",
        "source_id": source_id,
        "source_url": source_url,
        "published_at": pub,
        "fetched_at": fetched_at,
        "evidence_status": "reported",
        "source_record_id": event_key,
    }
    note_prefix = f"Trusted news report of SBV policy event {event_key}; effective {eff}."
    return [
        {
            **common,
            "indicator_id": "policy-refinancing-rate",
            "value": refinancing,
            "methodology_note": note_prefix + " Refinancing rate. Event-driven fallback evidence; no scalar inference.",
        },
        {
            **common,
            "indicator_id": "policy-rediscount-rate",
            "value": rediscount,
            "methodology_note": note_prefix + " Rediscount rate. Event-driven fallback evidence.",
        },
        {
            **common,
            "indicator_id": "policy-overnight-lending-rate",
            "value": overnight,
            "methodology_note": note_prefix + " SBV overnight lending/clearing-deficit facility rate; distinct from the market interbank overnight rate.",
        },
    ]


def _anchor_context(a) -> str:
    parts = [compact(" ".join(a.stripped_strings))]
    node = a
    for _ in range(4):
        node = getattr(node, "parent", None)
        if node is None:
            break
        t = compact(" ".join(node.stripped_strings))
        if 0 < len(t) <= 1200:
            parts.append(t)
        if getattr(node, "name", None) in {"article", "li"}:
            break
    return " ".join(dict.fromkeys(x for x in parts if x))


def _date_key(text: str):
    for pat in [
        r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b",
        r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",
    ]:
        m = re.search(pat, text)
        if m:
            if pat.startswith(r"\b(20"):
                return int(m.group(1)) * 10000 + int(m.group(2)) * 100 + int(m.group(3))
            return int(m.group(3)) * 10000 + int(m.group(2)) * 100 + int(m.group(1))
    return 0


def discover_policy_news_url(html: str, landing_url: str, allowed_domain: str | None = None):
    soup = BeautifulSoup(html, "lxml")
    ranked = []
    for idx, a in enumerate(soup.find_all("a", href=True)):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        title = compact(" ".join(a.stripped_strings))
        context = _anchor_context(a)
        haystack = f"{title} {context}"
        if not AUTHORITY_TERMS.search(haystack):
            continue
        # Deliberately target change/event reporting; forecasts saying the rate
        # may be held at 4.5% must not supersede an actual decision event.
        if not POLICY_EVENT_TERMS.search(haystack):
            continue
        if not re.search(r"điều\s+chỉnh|giảm|hạ|tăng|quyết\s+định", haystack, re.I):
            continue
        url = urljoin(landing_url, href)
        host = urlparse(url).netloc.lower()
        if allowed_domain and allowed_domain not in host:
            continue
        score = 0
        if re.search(r"lãi\s+suất\s+điều\s+hành", title, re.I): score += 8
        if re.search(r"Ngân\s+hàng\s+Nhà\s+nước|\bNHNN\b", title, re.I): score += 5
        if re.search(r"điều\s+chỉnh|giảm|hạ|tăng", title, re.I): score += 4
        if DECISION_RE.search(context): score += 6
        score += min(_date_key(context) // 10000, 9999)
        ranked.append((score, _date_key(context), -idx, url))
    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][3]
