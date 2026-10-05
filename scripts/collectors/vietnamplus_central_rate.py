from __future__ import annotations
from datetime import date
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

SOURCE_ID = "vna-vietnamplus"

_MONTHS = {
    name.lower(): idx for idx, name in enumerate([
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ], 1)
}
_MONTH_PATTERN = "|".join(m.title() for m in _MONTHS)


def _published_date(soup: BeautifulSoup, text: str):
    for attrs in [{"property": "article:published_time"}, {"name": "date"}, {"name": "publish-date"}]:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", tag["content"])
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(
        rf"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+({_MONTH_PATTERN})\s+(\d{{1,2}}),\s+(20\d{{2}})",
        text,
        re.I,
    )
    if not m:
        m = re.search(rf"({_MONTH_PATTERN})\s+(\d{{1,2}}),\s+(20\d{{2}})", text, re.I)
    if m:
        return f"{m.group(3)}-{_MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
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
            rate = float(m.group(1).replace(",", "").replace(".", ""))
            break
    if rate is None:
        return []
    published_at = _published_date(soup, text)
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
        "methodology_note": "VNA/VietnamPlus report citing the State Bank of Vietnam daily reference rate; fallback evidence only.",
    }]


def _date_key(text: str):
    """Return a sortable YYYYMMDD integer from VietnamPlus listing text, else None."""
    if not text:
        return None
    patterns = [
        r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",
        r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b",
        rf"\b({_MONTH_PATTERN})\s+(\d{{1,2}}),\s*(20\d{{2}})\b",
        rf"\b(\d{{1,2}})\s+({_MONTH_PATTERN})\s+(20\d{{2}})\b",
    ]
    for idx, pat in enumerate(patterns):
        m = re.search(pat, text, re.I)
        if not m:
            continue
        try:
            if idx == 0:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            elif idx == 1:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            elif idx == 2:
                mo, d, y = _MONTHS[m.group(1).lower()], int(m.group(2)), int(m.group(3))
            else:
                d, mo, y = int(m.group(1)), _MONTHS[m.group(2).lower()], int(m.group(3))
            date(y, mo, d)  # validate
            return y * 10_000 + mo * 100 + d
        except (ValueError, KeyError):
            continue
    return None


def _candidate_context(a) -> str:
    """Use the smallest nearby card-like container so the date belongs to this article."""
    texts = [" ".join(a.stripped_strings)]
    node = a
    for _ in range(4):
        node = getattr(node, "parent", None)
        if node is None:
            break
        if getattr(node, "name", None) in {"article", "li"}:
            texts.append(" ".join(node.stripped_strings))
            break
        cls = " ".join(node.get("class", [])) if hasattr(node, "get") else ""
        if re.search(r"article|story|item|news|card|box", cls, re.I):
            texts.append(" ".join(node.stripped_strings))
            break
        # Keep compact parent text as a fallback, but avoid swallowing the whole page.
        parent_text = " ".join(node.stripped_strings)
        if 0 < len(parent_text) <= 1200:
            texts.append(parent_text)
    return " ".join(dict.fromkeys(t for t in texts if t))


def discover_vietnamplus_central_rate_url(html: str, landing_url: str):
    """
    Select the newest reference-rate article by publication date, not DOM position.

    VietnamPlus tag pages can temporarily surface an older article above a newly-published
    one. The previous index-based ranking could therefore keep October 2 even when an
    October 5 article was present lower on the page. Dates now dominate ranking; DOM order
    is only a final tie-breaker.
    """
    soup = BeautifulSoup(html, "lxml")
    ranked = []
    landing_path = urlparse(landing_url).path.rstrip("/").lower()

    for idx, a in enumerate(soup.find_all("a", href=True)):
        txt = " ".join(a.stripped_strings).strip()
        href = (a.get("href") or "").strip()
        if not href:
            continue

        # Be specific enough for broad State Bank/VietnamPlus listing pages.
        relevant = bool(re.search(r"(?:daily\s+)?reference\s+exchange\s+rate|central\s+exchange\s+rate", txt, re.I))
        if not relevant:
            continue

        url = urljoin(landing_url, href)
        path = urlparse(url).path.lower()
        if "tag" in path or path.rstrip("/") == landing_path:
            continue
        if not path.endswith(".vnp"):
            continue

        context = _candidate_context(a)
        dkey = _date_key(context)
        specificity = 0
        if re.search(r"daily\s+reference\s+exchange\s+rate", txt, re.I):
            specificity += 30
        if re.search(r"reference\s+exchange\s+rate", txt, re.I):
            specificity += 20
        if re.search(r"State\s+Bank|SBV", context, re.I):
            specificity += 5

        # Dated cards always outrank undated cards; newest date wins.
        ranked.append((1 if dkey is not None else 0, dkey or 0, specificity, -idx, url))

    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][-1]
