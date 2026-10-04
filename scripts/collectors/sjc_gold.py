from __future__ import annotations
import re
from bs4 import BeautifulSoup

SOURCE_ID = "sjc"


def parse_sjc_gold(html: str, source_url: str, fetched_at: str):
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)
    ts = re.search(r"(\d{1,2}:\d{2})\s+(\d{1,2})/(\d{1,2})/(\d{4})", text)
    data_date = f"{ts.group(4)}-{int(ts.group(3)):02d}-{int(ts.group(2)):02d}" if ts else None
    published_at = f"{data_date}T{ts.group(1)}:00+07:00" if ts and data_date else None

    # Prefer table row matching SJC 1L/10L/1KG and HCMC section.
    row = None
    for tr in soup.find_all("tr"):
        cells = [" ".join(td.stripped_strings) for td in tr.find_all(["td","th"])]
        joined = " | ".join(cells)
        if re.search(r"Vàng\s+SJC\s+1L.*10L.*1KG", joined, re.I) and len(cells) >= 3:
            row = cells
            break
    if not row:
        # Text fallback for fixture/simple extraction.
        m = re.search(r"Vàng\s+SJC\s+1L,\s*10L,\s*1KG\s*[|:]\s*([\d,.]+)\s*[|]\s*([\d,.]+)", text, re.I)
        if not m: return []
        buy_raw, sell_raw = m.group(1), m.group(2)
    else:
        buy_raw, sell_raw = row[-2], row[-1]

    def parse_thousand_vnd(s):
        n = float(re.sub(r"[^0-9.]", "", s.replace(",", "")))
        # SJC main page states unit thousand VND/tael.
        return n * 1000

    buy, sell = parse_thousand_vnd(buy_raw), parse_thousand_vnd(sell_raw)
    common = {
        "period": data_date,
        "period_type": "day",
        "data_date": data_date,
        "unit": "vnd-per-tael",
        "source_id": SOURCE_ID,
        "source_url": source_url,
        "published_at": published_at,
        "fetched_at": fetched_at,
        "evidence_status": "verified",
        "methodology_note": "SJC quoted price for gold bar 1L/10L/1KG; source page unit is thousand VND per tael."
    }
    return [
        {**common, "indicator_id":"sjc-gold-bar-buy", "value":buy},
        {**common, "indicator_id":"sjc-gold-bar-sell", "value":sell}
    ]
