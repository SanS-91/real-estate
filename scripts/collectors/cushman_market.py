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
            "metric_qualifiers":{
                "new_supply":"approx",
                "sales_units":"approx",
                "absorption_rate":"approx"
            },
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
            "metric_qualifiers":{
                "new_supply_lower_bound":"greater-than",
                "absorption_rate":"exact"
            },
            "evidence_text":"Cushman & Wakefield states apartment new supply was over 1,300 units, so exact new_supply remains blank; absorption is source-published."
        })
    return rows


def parse_article(html: str, source_url: str, fetched_at: str):
    soup=BeautifulSoup(html,"lxml")
    title=(soup.find("h1").get_text(" ",strip=True) if soup.find("h1") else "Ho Chi Minh City Residential MarketBeat")
    text=" ".join(soup.stripped_strings)
    summary_bits=[]
    if re.search(r"over\s*1,300\s*units",text,re.I):
        summary_bits.append("Apartment new supply exceeded 1,300 units in Q2 2026")
    if re.search(r"absorption rate of\s*31%",text,re.I):
        summary_bits.append("apartment absorption was 31%")
    if re.search(r"approximately\s*1,700\s*units",text,re.I):
        summary_bits.append("landed new supply was approximately 1,700 units")
    if re.search(r"absorption rate of\s*~?\s*36%",text,re.I):
        summary_bits.append("landed absorption was about 36%")
    return {
        "title":title,
        "published_date":"2026-08-01",
        "summary":"; ".join(summary_bits) if summary_bits else "Cushman & Wakefield HCMC Residential MarketBeat Q2 2026 research update.",
        "tags":["residential","hcmc","q2-2026","supply","absorption"],
        "source_url":source_url,
        "fetched_at":fetched_at,
    }
