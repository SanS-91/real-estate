from __future__ import annotations

import re
from bs4 import BeautifulSoup

SOURCE_ID = "sbv-vietnam"


def _num(raw: str | None):
    if raw is None: return None
    return float(raw.strip().replace(".", "").replace(",", ".")) if "," in raw else float(raw.strip())


def _dates(text: str):
    vals=[]
    for m in re.finditer(r"\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b",text):
        vals.append((int(m.group(3)),int(m.group(2)),int(m.group(1))))
    if not vals: return None
    y,m,d=max(vals)
    return f"{y:04d}-{m:02d}-{d:02d}"


def parse_sbv_interbank_rates(html: str, source_url: str, fetched_at: str):
    """Parse the VND overnight interbank market rate from the official SBV statistics page."""
    soup=BeautifulSoup(html,"lxml")
    text=" ".join(soup.stripped_strings)
    data_date=_dates(text)

    value=None
    # Prefer a table row explicitly labelled VND + overnight/qua đêm.
    for tr in soup.find_all("tr"):
        row=" ".join(tr.stripped_strings)
        if not re.search(r"qua\s+đêm|overnight",row,re.I):
            continue
        if re.search(r"USD",row,re.I) and not re.search(r"VND|đồng\s+Việt\s+Nam",row,re.I):
            continue
        nums=re.findall(r"(?<!\d)(\d{1,2}(?:[.,]\d{1,4})?)(?!\d)",row)
        # Ignore term labels/dates; select a plausible percentage from the row.
        plausible=[_num(x) for x in nums if 0 <= _num(x) <= 30]
        if plausible:
            value=plausible[-1]
            break

    if value is None:
        patterns=[
            r"(?:VND[^.]{0,220}?)?(?:qua\s+đêm|overnight)[^\d]{0,100}([\d.,]+)\s*%",
            r"lãi\s+suất\s+(?:bình\s+quân\s+)?liên\s+ngân\s+hàng[^.]{0,260}?(?:qua\s+đêm|overnight)[^\d]{0,100}([\d.,]+)",
        ]
        for pat in patterns:
            m=re.search(pat,text,re.I|re.S)
            if m:
                value=_num(m.group(1)); break

    if value is None:
        return []
    return [{
        "indicator_id":"interbank-on",
        "period":data_date,
        "period_type":"date",
        "data_date":data_date,
        "value":value,
        "unit":"percent-per-year",
        "source_id":SOURCE_ID,
        "source_url":source_url,
        "published_at":data_date,
        "fetched_at":fetched_at,
        "evidence_status":"verified",
        "methodology_note":"Official SBV VND overnight interbank market rate. This market rate is distinct from the SBV overnight lending facility/policy rate.",
    }]
