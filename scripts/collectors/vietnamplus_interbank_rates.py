from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

SOURCE_ID = "vna-vietnamplus"


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or " ").strip()


def _num(raw: str | None):
    return float(raw.strip().replace(",", ".")) if raw else None


def _published_at(soup: BeautifulSoup, text: str):
    for attrs in ({"property":"article:published_time"},{"name":"date"},{"name":"publish-date"}):
        tag=soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            m=re.search(r"(20\d{2})-(\d{2})-(\d{2})", tag["content"])
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m=re.search(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b", text)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def _data_date(text: str, published_at: str | None):
    year=int(published_at[:4]) if published_at else None
    # Prefer the explicitly described trading session, e.g. "phiên 27/8".
    for pat in [
        r"(?:phiên(?:\s+giao\s+dịch)?|ngày)\s+(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?",
        r"trong\s+phiên\s+(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?",
    ]:
        m=re.search(pat, text, re.I)
        if m:
            y=int(m.group(3)) if m.group(3) else year
            if y:
                return f"{y:04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return published_at


def parse_vietnamplus_interbank_rates(html: str, source_url: str, fetched_at: str):
    soup=BeautifulSoup(html, "lxml")
    text=_compact(" ".join(soup.stripped_strings))
    published=_published_at(soup,text)
    data_date=_data_date(text,published)

    value=None
    patterns=[
        r"lãi\s+suất\s+qua\s+đêm[^.]{0,220}?(?:xuống|tăng|còn|ở\s+mức)\s*(?:còn\s*)?([0-9]+(?:[,.][0-9]+)?)\s*%\s*/?\s*năm",
        r"lãi\s+suất\s+bình\s+quân(?:\s+liên\s+ngân\s+hàng)?\s+bằng\s+VND[^.]{0,260}?kỳ\s+hạn\s+qua\s+đêm[^.]{0,180}?(?:xuống|tăng|còn|ở\s+mức)\s*(?:còn\s*)?([0-9]+(?:[,.][0-9]+)?)\s*%",
        r"overnight\s+interbank\s+rate[^.]{0,180}?(?:stood\s+at|fell\s+to|rose\s+to)\s+(?:about\s+)?([0-9]+(?:[,.][0-9]+)?)\s*(?:per\s+cent|%)",
    ]
    for pat in patterns:
        m=re.search(pat,text,re.I|re.S)
        if m:
            value=_num(m.group(1)); break
    if value is None or not (0 <= value <= 30):
        return []

    return [{
        "indicator_id":"interbank-on",
        "period":data_date,
        "period_type":"date",
        "data_date":data_date,
        "value":value,
        "unit":"percent-per-year",
        "source_id":SOURCE_ID,
        "source_url":source_url,
        "published_at":published,
        "fetched_at":fetched_at,
        "evidence_status":"reported",
        "methodology_note":"VietnamPlus/VNA fallback report for the VND overnight interbank market rate. Candidate evidence only until direct SBV verification or independent same-date corroboration.",
    }]


def _date_key(text: str):
    m=re.search(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b", text)
    if m:
        return int(m.group(3))*10000+int(m.group(2))*100+int(m.group(1))
    return 0


def _context(a):
    vals=[_compact(" ".join(a.stripped_strings))]
    node=a
    for _ in range(4):
        node=getattr(node,"parent",None)
        if node is None: break
        t=_compact(" ".join(node.stripped_strings))
        if 0 < len(t) <= 1200: vals.append(t)
        if getattr(node,"name",None) in {"article","li"}: break
    return " ".join(dict.fromkeys(x for x in vals if x))


def discover_vietnamplus_interbank_rates_url(html: str, landing_url: str):
    soup=BeautifulSoup(html,"lxml")
    ranked=[]
    landing_path=urlparse(landing_url).path.rstrip("/").lower()
    for idx,a in enumerate(soup.find_all("a",href=True)):
        href=(a.get("href") or "").strip()
        if not href: continue
        title=_compact(" ".join(a.stripped_strings))
        ctx=_context(a)
        blob=f"{title} {ctx}"
        if not re.search(r"lãi\s+suất\s+(?:liên\s+ngân\s+hàng|vay\s+mượn\s+qua\s+đêm)|qua\s+đêm.*liên\s+ngân\s+hàng", blob, re.I):
            continue
        url=urljoin(landing_url,href)
        path=urlparse(url).path.lower()
        if "tag" in path or path.rstrip("/")==landing_path: continue
        ranked.append((_date_key(blob)*1000-idx,url))
    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][1]
