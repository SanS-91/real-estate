from __future__ import annotations
import re
from bs4 import BeautifulSoup

SOURCE_ID = "baonghean-gold"


def _parse_vnd(raw: str | None):
    if not raw:
        return None
    digits = re.sub(r"[^0-9]", "", raw)
    return float(digits) if digits else None


def parse_baonghean_gold(html: str, source_url: str, fetched_at: str):
    """Parse Báo Nghệ An's live SJC tracker as trusted-media fallback evidence.

    The page publishes explicit SJC buy/sell values in VND/tael and an update timestamp.
    This source is evidence-only; it never replaces a direct SJC quote by itself.
    """
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)

    # Examples: "Cập nhật lúc 17:53 ngày 04/10/2026" or "Cập nhật 17:53 ngày 04/10/2026"
    ts = re.search(r"Cập\s+nhật(?:\s+trực\s+tiếp)?(?:\s+lúc)?\s*(\d{1,2}:\d{2})\s+ngày\s+(\d{1,2})/(\d{1,2})/(20\d{2})", text, re.I)
    if ts:
        hhmm, dd, mm, yyyy = ts.group(1), int(ts.group(2)), int(ts.group(3)), ts.group(4)
        data_date = f"{yyyy}-{mm:02d}-{dd:02d}"
        published_at = f"{data_date}T{hhmm}:00+07:00"
    else:
        dm = re.search(r"(\d{1,2})/(\d{1,2})/(20\d{2})", text)
        data_date = f"{dm.group(3)}-{int(dm.group(2)):02d}-{int(dm.group(1)):02d}" if dm else None
        published_at = data_date

    buy = sell = None

    # Strongest pattern on the dedicated tracker page.
    m = re.search(
        r"Giá\s+vàng\s+SJC\s+hôm\s+nay\s+niêm\s+yết\s+([\d.]+)\s*(?:đ|đồng)?/lượng\s*\(mua\s+vào\)\s+và\s+([\d.]+)\s*(?:đ|đồng)?/lượng\s*\(bán\s+ra\)",
        text, re.I,
    )
    if m:
        buy, sell = _parse_vnd(m.group(1)), _parse_vnd(m.group(2))

    # Table/card fallback: HCMC SJC 1L/10L/1KG followed by Mua vào / Bán ra.
    if buy is None:
        m = re.search(
            r"TP\.?\s*Hồ\s+Chí\s+Minh\s+Vàng\s+SJC\s+1L,?\s*10L,?\s*1KG.{0,220}?Mua\s+vào\s+([\d.]+).{0,120}?Bán\s+ra\s+([\d.]+)",
            text, re.I | re.S,
        )
        if m:
            buy, sell = _parse_vnd(m.group(1)), _parse_vnd(m.group(2))

    # Compact fallback from top summary.
    if buy is None:
        m = re.search(r"SJC\s+mua\s+vào\s+([\d.]+).{0,100}?SJC\s+bán\s+ra\s+([\d.]+)", text, re.I | re.S)
        if m:
            buy, sell = _parse_vnd(m.group(1)), _parse_vnd(m.group(2))

    if buy is None or sell is None or buy <= 0 or sell <= 0:
        return []

    common = {
        "period": data_date,
        "period_type": "day",
        "data_date": data_date,
        "unit": "vnd-per-tael",
        "source_id": SOURCE_ID,
        "source_url": source_url,
        "published_at": published_at,
        "fetched_at": fetched_at,
        "evidence_status": "reported",
        "methodology_note": "Báo Nghệ An live SJC tracker aggregating public dealer quotes. Trusted-media fallback evidence; not a substitute for direct SJC verification.",
    }
    return [
        {**common, "indicator_id": "sjc-gold-bar-buy", "value": buy},
        {**common, "indicator_id": "sjc-gold-bar-sell", "value": sell},
    ]
