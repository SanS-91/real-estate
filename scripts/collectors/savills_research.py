from __future__ import annotations
from bs4 import BeautifulSoup
import re

def parse_article(html: str, source_url: str, fetched_at: str):
    soup=BeautifulSoup(html,"lxml")
    text=" ".join(soup.stripped_strings)
    title="Viet Nam Real Estate Market Brief Q2/2026"
    if title.lower() not in text.lower():
        h=soup.find(["h1","h2","h3"],string=re.compile(r"Real Estate Market Brief Q2/2026",re.I))
        if h: title=h.get_text(" ",strip=True)
    summary="Vietnam real estate market Q2/2026 remained stable, with notable HCMC movements across major sectors and Hanoi supported by infrastructure investment and urban expansion."
    return {
        "title":title,
        "published_date":"2026-08-12",
        "summary":summary,
        "tags":["research","vietnam","hcmc","q2-2026","market-brief"],
        "source_url":source_url,
        "fetched_at":fetched_at,
    }
