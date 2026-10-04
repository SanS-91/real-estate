from __future__ import annotations
import re
from bs4 import BeautifulSoup

SOURCE_ID = "sbv-vietnam"


def parse_sbv_central_rate(html: str, source_url: str, fetched_at: str):
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)
    m_rate = re.search(r"1\s*Đô\s*la\s*Mỹ\s*=\s*([\d.]+)\s*VND", text, re.I)
    m_date = re.search(r"(?:Ngày\s+ban\s+hành|áp\s+dụng\s+cho\s+ngày)\s*[:]?\s*(\d{1,2})/(\d{1,2})/(\d{4})", text, re.I)
    if not (m_rate and m_date): return []
    value = float(m_rate.group(1).replace(".", ""))
    data_date = f"{m_date.group(3)}-{int(m_date.group(2)):02d}-{int(m_date.group(1)):02d}"
    return [{
        "indicator_id":"usd-vnd-central-rate",
        "period":data_date,"period_type":"day","data_date":data_date,
        "value":value,"unit":"vnd-per-usd","source_id":SOURCE_ID,
        "source_url":source_url,"published_at":data_date,"fetched_at":fetched_at,
        "evidence_status":"verified",
        "methodology_note":"Official SBV central USD/VND rate; direct official record required for canonical publication."
    }]
