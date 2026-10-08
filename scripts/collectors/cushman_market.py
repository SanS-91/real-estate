from __future__ import annotations

import re
from bs4 import BeautifulSoup

def _text(html: str) -> str:
    soup=BeautifulSoup(html,"lxml")
    for tag in soup(["script","style","noscript"]):
        tag.decompose()
    return " ".join(soup.stripped_strings)

def parse(html: str, source_url: str, fetched_at: str):
    text=_text(html)
    rows=[]

    # Landed Q2/2026 public MarketBeat publishes approximately 1,700 new units,
    # ~36% absorption and nearly 870 absorbed/sold units. Keep approximation in note.
    landed_supply=None
    m=re.search(r"(?:landed property|primary market)[^\.]{0,220}?approximately\s*([\d,]+)\s*units",text,re.I)
    if m:
        landed_supply=int(m.group(1).replace(",",""))

    landed_abs=None
    m=re.search(r"absorption rate of\s*~?\s*([\d.]+)%[^\.]{0,120}?nearly\s*([\d,]+)\s*units",text,re.I)
    landed_sales=None
    if m:
        landed_abs=float(m.group(1))/100
        landed_sales=int(m.group(2).replace(",",""))

    if landed_supply is not None or landed_abs is not None or landed_sales is not None:
        rows.append({
            "segment_id":"landed",
            "new_supply":landed_supply,
            "sales_units":landed_sales,
            "absorption_rate":landed_abs,
            "average_asp":None,
            "evidence_text":"Cushman & Wakefield HCMC Residential MarketBeat Q2/2026; published figures are approximate where stated by source."
        })

    # Apartment page states 'over 1,300 units'; do not coerce the lower bound into an exact count.
    m=re.search(r"new supply[^\.]{0,160}?over\s*([\d,]+)\s*units",text,re.I)
    apartment_abs=None
    ma=re.search(r"absorption rate of\s*([\d.]+)%\s*of newly launched primary supply",text,re.I)
    if ma:
        apartment_abs=float(ma.group(1))/100
    if m or apartment_abs is not None:
        rows.append({
            "segment_id":"apartment",
            "new_supply":None,
            "sales_units":None,
            "absorption_rate":apartment_abs,
            "average_asp":None,
            "lower_bound_new_supply":int(m.group(1).replace(",","")) if m else None,
            "evidence_text":"Cushman & Wakefield states apartment new supply was over 1,300 units, so exact new_supply remains blank; absorption is source-published."
        })
    return rows
