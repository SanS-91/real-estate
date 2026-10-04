from __future__ import annotations
import re
from bs4 import BeautifulSoup

SOURCE_ID = "pnj-gold"


def parse_pnj_gold(html: str, source_url: str, fetched_at: str):
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)
    ts = re.search(r"Giá\s+vàng\s+ngày\s*:\s*(\d{1,2})/(\d{1,2})/(20\d{2})\s+(\d{1,2}:\d{2}(?::\d{2})?)", text, re.I)
    data_date = f"{ts.group(3)}-{int(ts.group(2)):02d}-{int(ts.group(1)):02d}" if ts else None
    published_at = f"{data_date}T{ts.group(4)[:5]}:00+07:00" if ts and data_date else None

    buy = sell = None
    for tr in soup.find_all("tr"):
        cells = [" ".join(td.stripped_strings) for td in tr.find_all(["td", "th"])]
        joined = " | ".join(cells)
        if re.search(r"\bTPHCM\b|TP\.?(?:\s*)HCM|Hồ\s+Chí\s+Minh", joined, re.I) and re.search(r"\bSJC\b", joined, re.I):
            nums = [c for c in cells if re.search(r"\d", c)]
            if len(cells) >= 4:
                buy, sell = cells[-2], cells[-1]
                break
    if buy is None:
        # Text fallback matching TPHCM SJC 144.600 147.600 / 144,600 147,600.
        m = re.search(r"TPHCM\s+SJC\s+([\d.,]+)\s+([\d.,]+)", text, re.I)
        if m:
            buy, sell = m.group(1), m.group(2)
    if buy is None:
        return []

    def parse_thousand_vnd_per_tael(raw: str):
        raw = re.sub(r"[^0-9.,]", "", raw)
        # PNJ uses dot as thousands separator in Vietnamese display (e.g. 144.600).
        digits = re.sub(r"[.,]", "", raw)
        return float(digits) * 1000

    b, s = parse_thousand_vnd_per_tael(buy), parse_thousand_vnd_per_tael(sell)
    common = {
        "period": data_date, "period_type": "day", "data_date": data_date,
        "unit": "vnd-per-tael", "source_id": SOURCE_ID, "source_url": source_url,
        "published_at": published_at, "fetched_at": fetched_at,
        "evidence_status": "corroborated",
        "methodology_note": "PNJ public price board quoting SJC product in HCMC; fallback quote for SJC gold-bar series. Source unit is thousand VND/tael.",
    }
    return [
        {**common, "indicator_id": "sjc-gold-bar-buy", "value": b},
        {**common, "indicator_id": "sjc-gold-bar-sell", "value": s},
    ]
