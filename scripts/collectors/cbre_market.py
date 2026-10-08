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
    apartment=None
    landed=None

    patterns_apartment=[
        r"(?:Condominium supply|Nguồn cung căn hộ)[^\.]{0,160}?(?:only|chỉ)\s*([\d.,]+)\s*(?:units|căn)",
        r"(?:căn hộ|condominium)[^\.]{0,120}?([\d.,]+)\s*(?:units|căn)[^\.]{0,80}?(?:launched|chào bán|mở bán)",
    ]
    patterns_landed=[
        r"(?:landed property market|phân khúc BĐS thấp tầng)[^\.]{0,200}?(?:recording|ghi nhận)\s*([\d.,]+)\s*(?:newly launched units|sản phẩm mở bán mới)",
    ]

    for p in patterns_apartment:
        m=re.search(p,text,re.I)
        if m:
            apartment=int(re.sub(r"\D","",m.group(1)))
            break
    for p in patterns_landed:
        m=re.search(p,text,re.I)
        if m:
            landed=int(re.sub(r"\D","",m.group(1)))
            break

    rows=[]
    if apartment is not None:
        rows.append({
            "segment_id":"apartment",
            "new_supply":apartment,
            "evidence_text":"CBRE residential Q2 figure: condominium units launched.",
        })
    if landed is not None:
        rows.append({
            "segment_id":"landed",
            "new_supply":landed,
            "evidence_text":"CBRE residential Q2 figure: newly launched landed-property units.",
        })
    return rows
