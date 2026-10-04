from __future__ import annotations
import re
from bs4 import BeautifulSoup

SOURCE_ID = "vov"


def parse_vov_central_rate(html: str, source_url: str, fetched_at: str):
    soup=BeautifulSoup(html,"lxml")
    text=" ".join(soup.stripped_strings)
    m = re.search(r"tỷ\s+giá\s+trung\s+tâm[^.]{0,100}?(?:mức|đạt)\s+([\d.]+)\s*(?:đồng|VND)/?USD", text, re.I)
    d = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if not m: return []
    value=float(m.group(1).replace('.',''))
    data_date = f"{d.group(3)}-{int(d.group(2)):02d}-{int(d.group(1)):02d}" if d else None
    return [{
        "indicator_id":"usd-vnd-central-rate","period":data_date,"period_type":"day","data_date":data_date,
        "value":value,"unit":"vnd-per-usd","source_id":SOURCE_ID,"source_url":source_url,
        "published_at":data_date,"fetched_at":fetched_at,"evidence_status":"reported",
        "methodology_note":"Trusted-media report citing SBV. Corroboration only; does not replace direct SBV canonical record."
    }]


def discover_vov_central_rate_url(html: str, landing_url: str):
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        txt = " ".join(a.stripped_strings)
        href = a.get("href")
        if re.search(r"tỷ\s+giá\s+trung\s+tâm|tỷ\s+giá.*USD|USD.*VND", txt, re.I):
            return urljoin(landing_url, href)
    return None
