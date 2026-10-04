from __future__ import annotations
import re
from bs4 import BeautifulSoup

SOURCE_ID = "doji-gold"


def parse_doji_gold(html: str, source_url: str, fetched_at: str):
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)
    dm = re.search(r"ngày\s+(\d{1,2})[-/]\s*(\d{1,2})[-/]\s*(20\d{2})", text, re.I)
    tm = re.search(r"(?:giờ|Cập\s+nhập\s+lúc)\s*[:]?\s*(\d{1,2}:\d{2})", text, re.I)
    data_date = f"{dm.group(3)}-{int(dm.group(2)):02d}-{int(dm.group(1)):02d}" if dm else None
    published_at = f"{data_date}T{tm.group(1)}:00+07:00" if data_date and tm else None
    buy = sell = None
    for tr in soup.find_all("tr"):
        cells = [" ".join(td.stripped_strings) for td in tr.find_all(["td", "th"])]
        if cells and re.search(r"SJC.*Bán\s*Lẻ", " | ".join(cells), re.I) and len(cells) >= 3:
            buy, sell = cells[-2], cells[-1]
            break
    if buy is None:
        m = re.search(r"SJC\s*-?\s*Bán\s*Lẻ[^\d]{0,40}([\d,.]+)\s+([\d,.]+)", text, re.I)
        if m:
            buy, sell = m.group(1), m.group(2)
    if buy is None:
        return []

    unit_per_chi = bool(re.search(r"ngh[iì]n(?:\s*VNĐ)?\s*/\s*chỉ", text, re.I))
    unit_per_tael = bool(re.search(r"ngh[iì]n(?:\s*VNĐ)?\s*/\s*(?:lượng|luong)", text, re.I))

    def parse_vnd_per_tael(raw: str):
        digits = re.sub(r"[^0-9]", "", raw)
        if not digits:
            raise ValueError("DOJI quote missing numeric value")
        n = float(digits)
        if unit_per_tael:
            return n * 1000
        # Legacy DOJI pages commonly state 'nghìn/chỉ'. 1 lượng = 10 chỉ.
        return n * 1000 * 10

    b, s = parse_vnd_per_tael(buy), parse_vnd_per_tael(sell)
    if b <= 0 or s <= 0:
        return []
    common = {
        "period": data_date, "period_type": "day", "data_date": data_date,
        "unit": "vnd-per-tael", "source_id": SOURCE_ID, "source_url": source_url,
        "published_at": published_at, "fetched_at": fetched_at,
        "evidence_status": "corroborated",
        "methodology_note": "DOJI public retail quote for SJC product; fallback evidence for SJC gold-bar series. Display is normally thousand VND/chi and converted to VND/tael.",
    }
    return [
        {**common, "indicator_id": "sjc-gold-bar-buy", "value": b},
        {**common, "indicator_id": "sjc-gold-bar-sell", "value": s},
    ]
