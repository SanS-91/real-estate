from __future__ import annotations

import re
from datetime import datetime
from bs4 import BeautifulSoup

SOURCE_ID = "sbv-vietnam-archive"
MONTHS = {m.lower(): i for i, m in enumerate([
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
], start=1)}


def _num(raw: str | None):
    if raw is None:
        return None
    return float(raw.strip().replace(",", "."))


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or " ").strip()


def _latest_table_row(text: str):
    rows=[]
    pat=re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\s+"
        r"([0-9]+(?:[.,][0-9]+)?)\s+([0-9]+(?:[.,][0-9]+)?)\s+([0-9]+(?:[.,][0-9]+)?)\b",
        re.I,
    )
    for m in pat.finditer(text):
        month=MONTHS[m.group(1).lower()]
        year=int(m.group(2))
        vals=(_num(m.group(3)), _num(m.group(4)), _num(m.group(5)))
        if all(v is not None and 0 <= v <= 30 for v in vals):
            rows.append((year, month, vals))
    return max(rows, default=None, key=lambda x:(x[0],x[1]))


def _fallback_trio(text: str):
    # Official SBV annual-report wording for the 2023 easing cycle.
    r1=re.search(r"(?:lãi\s+suất\s+)?tái\s+cấp\s+vốn[^.;]{0,180}?(?:xuống|ở\s+mức)?\s*([0-9]+(?:[.,][0-9]+)?)\s*%", text, re.I)
    r2=re.search(r"(?:lãi\s+suất\s+)?tái\s+chiết\s+khấu[^.;]{0,180}?(?:xuống|ở\s+mức)?\s*([0-9]+(?:[.,][0-9]+)?)\s*%", text, re.I)
    r3=re.search(r"lãi\s+suất\s+cho\s+vay\s+qua\s+đêm[^.;]{0,260}?(?:xuống|ở\s+mức)?\s*([0-9]+(?:[.,][0-9]+)?)\s*%", text, re.I)
    if r1 and r2 and r3:
        return (_num(r1.group(1)), _num(r2.group(1)), _num(r3.group(1)))
    # English archive wording.
    r1=re.search(r"refinancing\s+rate[^.;]{0,180}?([0-9]+(?:[.,][0-9]+)?)\s*%", text, re.I)
    r2=re.search(r"rediscount\s+rate[^.;]{0,180}?([0-9]+(?:[.,][0-9]+)?)\s*%", text, re.I)
    r3=re.search(r"overnight\s+lending\s+rate[^.;]{0,220}?([0-9]+(?:[.,][0-9]+)?)\s*%", text, re.I)
    if r1 and r2 and r3:
        return (_num(r1.group(1)), _num(r2.group(1)), _num(r3.group(1)))
    return None


def parse_sbv_policy_archive(html: str, source_url: str, fetched_at: str):
    """Parse an accessible official SBV archive snapshot of administered rates.

    This is deliberately not treated as a live canonical endpoint. The archive
    provides authoritative historical levels, but current production still needs
    a fresher direct capture or independent current corroboration.
    """
    soup=BeautifulSoup(html, "lxml")
    text=_compact(" ".join(soup.stripped_strings))

    row=_latest_table_row(text)
    if row:
        year,month,vals=row
        period=f"{year:04d}-{month:02d}"
        refinancing,rediscount,overnight=vals
    else:
        vals=_fallback_trio(text)
        if not vals:
            return []
        refinancing,rediscount,overnight=vals
        # The official annual-report snapshot documents the 2023 policy easing
        # cycle. Keep this as a historical snapshot, not a fabricated current date.
        period="2023-12"

    common={
        "period":period,
        "period_type":"month",
        "data_date":None,
        "unit":"percent-per-year",
        "source_id":SOURCE_ID,
        "source_url":source_url,
        "published_at":None,
        "fetched_at":fetched_at,
        "evidence_status":"reported",
    }
    note=(
        "Official SBV archive snapshot. Authoritative historical policy-rate level, "
        "but treated as fallback evidence because the live SBV statistics host is unreachable "
        "from the collector and the archive snapshot is not a fresh current-policy event."
    )
    return [
        {**common,"indicator_id":"policy-refinancing-rate","value":refinancing,"methodology_note":note},
        {**common,"indicator_id":"policy-rediscount-rate","value":rediscount,"methodology_note":note},
        {**common,"indicator_id":"policy-overnight-lending-rate","value":overnight,"methodology_note":note},
    ]
