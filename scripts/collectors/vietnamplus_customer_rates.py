from __future__ import annotations
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

SOURCE_ID = "vna-vietnamplus"
MONTHS_VI = {
    "một":1,"hai":2,"ba":3,"tư":4,"bốn":4,"năm":5,"sáu":6,
    "bảy":7,"tám":8,"chín":9,"mười":10,"mười một":11,"mười hai":12,
}


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
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def _period(text: str, published_at: str | None):
    # Monthly SBV rate articles often say "trong tháng Tám" while being published in September.
    # Use the article year and the explicitly named business month.
    year = None
    if published_at:
        year = int(published_at[:4])
    if year is None:
        y = re.search(r"\b(20\d{2})\b", text)
        year = int(y.group(1)) if y else None
    m = re.search(r"(?:trong|của|tháng)\s+tháng\s+([A-Za-zÀ-ỹ ]+?)\b", text, re.I)
    if not m:
        m = re.search(r"\btháng\s+(Tám|Bảy|Sáu|Năm|Chín|Mười(?:\s+Một|\s+Hai)?|Một|Hai|Ba|Tư|Bốn)\b", text, re.I)
    if m and year:
        token=_compact(m.group(1)).lower()
        token=token.replace("tháng ", "")
        if token in MONTHS_VI:
            return f"{year}-{MONTHS_VI[token]:02d}"
    # Explicit numeric month/year fallback.
    m=re.search(r"\btháng\s+(\d{1,2})/(20\d{2})\b", text, re.I)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    return None


def parse_vietnamplus_customer_rates(html: str, source_url: str, fetched_at: str):
    soup=BeautifulSoup(html, "lxml")
    text=_compact(" ".join(soup.stripped_strings))
    published_at=_published_at(soup, text)
    period=_period(text, published_at)
    if not period:
        return []

    # Lending range: bind to the actual post-change level after "lên/ở mức", not
    # the preceding month-on-month change such as 0.1%-0.2%.
    lend=None
    for pat in [
        r"lãi\s+suất\s+cho\s+vay\s+bình\s+quân[^.]{0,300}?(?:lên|ở\s+mức|dao\s+động\s+từ)\s*([\d,.]+)\s*%?\s*(?:-|–|—|đến)\s*([\d,.]+)\s*%\s*/?\s*năm",
        r"(?:cho\s+vay\s+bình\s+quân)[^.]{0,320}?\b([6-9]|1[0-5])(?:[,.]\d+)?\s*%\s*(?:-|–|—|đến)\s*([6-9]|1[0-5])(?:[,.]\d+)?\s*%\s*/?\s*năm",
    ]:
        m=re.search(pat, text, re.I|re.S)
        if m:
            lend=(_num(m.group(1)), _num(m.group(2))); break

    # Deposit 6–12M range: bind the value directly to the 6–12 month clause so the
    # preceding >24M range (7.2%-8.1%) cannot be selected by accident.
    dep=None
    for pat in [
        r"(?:từ\s+)?([\d,.]+)\s*%\s*(?:-|–|—|đến)\s*([\d,.]+)\s*%\s*/?\s*năm\s+đối\s+với\s+tiền\s+gửi[^.;]{0,160}?(?:từ\s+)?6\s*tháng\s+đến\s+12\s*tháng",
        r"(?:6\s*tháng\s+đến\s+12\s*tháng|từ\s+6\s*tháng\s+đến\s+12\s*tháng)[^.;]{0,160}?([\d,.]+)\s*%\s*(?:-|–|—|đến)\s*([\d,.]+)\s*%",
    ]:
        m=re.search(pat, text, re.I|re.S)
        if m:
            dep=(_num(m.group(1)), _num(m.group(2))); break

    priority=None
    m=re.search(r"lãi\s+suất\s+cho\s+vay\s+ngắn\s+hạn[^.]{0,220}?lĩnh\s+vực\s+ưu\s+tiên[^.]{0,160}?(?:lên|ở|khoảng|mức)?\s*([\d,.]+)\s*%\s*/?\s*năm", text, re.I|re.S)
    if m:
        priority=_num(m.group(1))

    common={
        "period":period,
        "period_type":"month",
        "unit":"percent-per-year",
        "source_id":SOURCE_ID,
        "source_url":source_url,
        "published_at":published_at,
        "fetched_at":fetched_at,
        "evidence_status":"reported",
    }
    out=[]
    if dep:
        lo,hi=dep
        out += [
            {**common,"indicator_id":"deposit-rate-vnd-6-12m-low","value":lo,"methodology_note":"VNA/VietnamPlus report citing SBV; lower bound of 6–12M VND deposit-rate range. Independent fallback evidence only."},
            {**common,"indicator_id":"deposit-rate-vnd-6-12m-high","value":hi,"methodology_note":"VNA/VietnamPlus report citing SBV; upper bound of 6–12M VND deposit-rate range. Independent fallback evidence only."},
        ]
    if lend:
        lo,hi=lend
        out += [
            {**common,"indicator_id":"lending-rate-vnd-average-low","value":lo,"methodology_note":"VNA/VietnamPlus report citing SBV; lower bound of average VND lending-rate range. Independent fallback evidence only."},
            {**common,"indicator_id":"lending-rate-vnd-average-high","value":hi,"methodology_note":"VNA/VietnamPlus report citing SBV; upper bound of average VND lending-rate range. Independent fallback evidence only."},
        ]
    if priority is not None:
        out.append({**common,"indicator_id":"priority-short-term-lending-rate-vnd","value":priority,"methodology_note":"VNA/VietnamPlus report citing SBV; reported approximate short-term VND lending rate for priority sectors. Independent fallback evidence; preserve source rounding."})
    return out


def _date_key(text: str):
    m=re.search(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b", text)
    if m:
        return int(m.group(3))*10000+int(m.group(2))*100+int(m.group(1))
    return 0


def _context(a) -> str:
    texts=[_compact(" ".join(a.stripped_strings))]
    node=a
    for _ in range(4):
        node=getattr(node,"parent",None)
        if node is None: break
        parent=_compact(" ".join(node.stripped_strings))
        if 0 < len(parent) <= 1000:
            texts.append(parent)
        if getattr(node,"name",None) in {"article","li"}:
            break
    return " ".join(dict.fromkeys(t for t in texts if t))


def discover_vietnamplus_customer_rates_url(html: str, landing_url: str):
    soup=BeautifulSoup(html,"lxml")
    ranked=[]
    landing_path=urlparse(landing_url).path.rstrip("/").lower()
    for idx,a in enumerate(soup.find_all("a",href=True)):
        title=_compact(" ".join(a.stripped_strings))
        href=(a.get("href") or "").strip()
        if not href: continue
        context=_context(a)
        # Target monthly SBV system-wide rate articles, not daily retail-rate stories.
        if not re.search(r"lãi\s+suất\s+cho\s+vay\s+bình\s+quân|chi\s+phí\s+vốn.*lãi\s+suất", title, re.I):
            continue
        if not re.search(r"Ngân\s+hàng\s+Nhà\s+nước|tháng\s+(?:Tám|Bảy|Sáu|Chín|Mười)", context, re.I):
            continue
        url=urljoin(landing_url,href)
        path=urlparse(url).path.lower()
        if "tag" in path or path.rstrip("/")==landing_path: continue
        score=_date_key(context)*1000 - idx
        ranked.append((score,url))
    if not ranked: return None
    ranked.sort(reverse=True)
    return ranked[0][1]
