from __future__ import annotations

import re
from bs4 import BeautifulSoup

SOURCE_ID = "vietnamnet-gold"


def _parse_vnd(raw: str | None):
    if not raw:
        return None
    digits = re.sub(r"[^0-9]", "", raw)
    return float(digits) if digits else None


def _page_timestamp(text: str):
    # Current live tracker shape: "Cập nhật lúc 22:38 ngày 04/10/2026"
    m = re.search(
        r"Cập\s+nhật(?:\s+trực\s+tiếp)?(?:\s+lúc)?\s*(\d{1,2}:\d{2})\s+ngày\s+(\d{1,2})/(\d{1,2})/(20\d{2})",
        text,
        re.I,
    )
    if m:
        hhmm, dd, mm, yyyy = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        date = f"{yyyy}-{mm:02d}-{dd:02d}"
        return date, f"{date}T{hhmm}:00+07:00"

    m = re.search(r"(\d{1,2})/(\d{1,2})/(20\d{2})", text)
    if m:
        date = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        return date, date
    return None, None


def _extract_from_rows(soup: BeautifulSoup):
    for tr in soup.find_all("tr"):
        row = " ".join(tr.stripped_strings)
        if not re.search(r"SJC", row, re.I):
            continue
        if not (re.search(r"1L", row, re.I) and re.search(r"10L", row, re.I) and re.search(r"1KG", row, re.I)):
            continue
        nums = re.findall(r"\b\d{2,3}(?:[.,]\d{3}){2}\b", row)
        if len(nums) >= 2:
            return _parse_vnd(nums[-2]), _parse_vnd(nums[-1])
    return None, None


def parse_vietnamnet_gold(html: str, source_url: str, fetched_at: str):
    """Parse VietnamNet's public gold tracker for HCMC SJC 1L/10L/1KG quote.

    The record remains reported evidence until independently corroborated or directly
    verified from SJC.
    """
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.stripped_strings)
    data_date, published_at = _page_timestamp(text)

    buy, sell = _extract_from_rows(soup)

    if buy is None or sell is None:
        # Flattened page fallback based on the current public tracker shape.
        patterns = [
            r"TP\.?\s*Hồ\s+Chí\s+Minh\s+Vàng\s+SJC\s+1L,?\s*10L,?\s*1KG.{0,260}?([\d.]{8,}).{0,120}?([\d.]{8,})",
            r"Vàng\s+SJC\s+1L,?\s*10L,?\s*1KG.{0,260}?([\d.]{8,}).{0,120}?([\d.]{8,})",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.S)
            if m:
                buy, sell = _parse_vnd(m.group(1)), _parse_vnd(m.group(2))
                break

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
        "methodology_note": "VietnamNet public gold tracker reporting the HCMC SJC 1L/10L/1KG buy/sell quote. Independent media corroboration; not a substitute for direct SJC verification.",
    }
    return [
        {**common, "indicator_id": "sjc-gold-bar-buy", "value": buy},
        {**common, "indicator_id": "sjc-gold-bar-sell", "value": sell},
    ]
