from __future__ import annotations

import re
from bs4 import BeautifulSoup

SOURCE_ID = "sbv-vietnam"


def _num(raw: str | None):
    if raw is None:
        return None
    return float(raw.strip().replace(".", "").replace(",", ".")) if "," in raw else float(raw.strip())


def _date(text: str):
    # Prefer explicit effective/application dates, then any machine-readable publication date.
    patterns = [
        r"(?:có\s+hiệu\s+lực|áp\s+dụng)\s+(?:kể\s+)?từ\s+ngày\s+(\d{1,2})[./-](\d{1,2})[./-](20\d{2})",
        r"ngày\s+(\d{1,2})[./-](\d{1,2})[./-](20\d{2})",
    ]
    for pat in patterns:
        m=re.search(pat,text,re.I)
        if m:
            return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def _published_at(soup: BeautifulSoup, text: str):
    for attrs in ({"property":"article:published_time"},{"name":"date"},{"itemprop":"datePublished"}):
        tag=soup.find("meta",attrs=attrs)
        if tag and tag.get("content"):
            m=re.search(r"(20\d{2})-(\d{2})-(\d{2})",tag["content"])
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return _date(text)


def _find(text: str, patterns: list[str]):
    for pat in patterns:
        m=re.search(pat,text,re.I|re.S)
        if m:
            return _num(m.group(1))
    return None


def parse_sbv_policy_rates(html: str, source_url: str, fetched_at: str):
    """Parse current SBV-administered policy rates from the official rate page.

    The page has historically exposed the refinancing, rediscount and SBV overnight
    lending/clearing-deficit rates. We keep these as separate event-driven series.
    """
    soup=BeautifulSoup(html,"lxml")
    text=" ".join(soup.stripped_strings)
    effective=_date(text)
    published_at=_published_at(soup,text)
    period=effective or published_at

    refinancing=_find(text,[
        r"lãi\s+suất\s+tái\s+cấp\s+vốn[^\d]{0,120}([\d.,]+)\s*%",
        r"tái\s+cấp\s+vốn[^\d]{0,120}([\d.,]+)\s*%",
        r"refinancing\s+(?:interest\s+)?rate[^\d]{0,120}([\d.,]+)\s*%",
    ])
    rediscount=_find(text,[
        r"lãi\s+suất\s+tái\s+chiết\s+khấu[^\d]{0,120}([\d.,]+)\s*%",
        r"tái\s+chiết\s+khấu[^\d]{0,120}([\d.,]+)\s*%",
        r"rediscount(?:ing)?\s+(?:interest\s+)?rate[^\d]{0,120}([\d.,]+)\s*%",
    ])
    overnight=_find(text,[
        r"(?:lãi\s+suất\s+)?cho\s+vay\s+qua\s+đêm[^.]{0,260}?(?:thanh\s+toán\s+điện\s+tử\s+liên\s+ngân\s+hàng|bù\s+đắp\s+thiếu\s+hụt)[^\d]{0,160}([\d.,]+)\s*%",
        r"overnight\s+(?:lending|loan)\s+rate[^\d]{0,160}([\d.,]+)\s*%",
    ])

    common={
        "period": period,
        "period_type": "event-date",
        "data_date": effective,
        "unit": "percent-per-year",
        "source_id": SOURCE_ID,
        "source_url": source_url,
        "published_at": published_at,
        "fetched_at": fetched_at,
        "evidence_status": "verified",
    }
    out=[]
    if refinancing is not None:
        out.append({**common,"indicator_id":"policy-refinancing-rate","value":refinancing,"methodology_note":"Official SBV-administered refinancing rate; event-driven series, preserving the effective date when exposed by the source."})
    if rediscount is not None:
        out.append({**common,"indicator_id":"policy-rediscount-rate","value":rediscount,"methodology_note":"Official SBV-administered rediscount rate; event-driven series."})
    if overnight is not None:
        out.append({**common,"indicator_id":"policy-overnight-lending-rate","value":overnight,"methodology_note":"Official SBV overnight lending / clearing-deficit facility rate; distinct from the market interbank overnight rate."})
    return out
