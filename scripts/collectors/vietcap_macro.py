from __future__ import annotations
import re
from bs4 import BeautifulSoup

SOURCE_ID="vietcap-research"


def parse_vietcap_macro(html: str, source_url: str, fetched_at: str):
    soup=BeautifulSoup(html,"lxml")
    title=(soup.find("h1").get_text(" ",strip=True) if soup.find("h1") else "Vietcap macro research")
    text=" ".join(soup.stripped_strings)
    d=re.search(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})", text, re.I)
    months={m.lower():i for i,m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],1)}
    pub = f"{d.group(3)}-{months[d.group(2).lower()]:02d}-{int(d.group(1)):02d}" if d else None
    facts=[]
    for pat, metric, unit in [
        (r"CPI[^.]{0,80}?rose\s+([\d.]+)%\s+YoY", "cpi-yoy", "percent"),
        (r"USD/VND\s+closed\s+at\s+([\d,]+)", "usd-vnd-market-close", "vnd-per-usd"),
        (r"GDP[^.]{0,80}?expanded\s+([\d.]+)%\s+YoY", "gdp-yoy", "percent")
    ]:
        m=re.search(pat,text,re.I)
        if m:
            val=float(m.group(1).replace(',',''))
            facts.append({"metric":metric,"value":val,"unit":unit})
    return {
        "source_id":SOURCE_ID,"title":title,"published_at":pub,"source_url":source_url,
        "fetched_at":fetched_at,"evidence_status":"reported","related_indicator_ids":[f["metric"] for f in facts],
        "facts":facts,"summary":"Research evidence only; values/forecasts are preserved with source context and do not overwrite official actual series."
    }


def discover_vietcap_macro_url(html: str, landing_url: str):
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        txt = " ".join(a.stripped_strings)
        href = a.get("href")
        if re.search(r"macro|macroeconomic", txt, re.I) and "/research-center/" in href:
            return urljoin(landing_url, href)
    return None
