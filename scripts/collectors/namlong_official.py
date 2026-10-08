from __future__ import annotations

import re
from bs4 import BeautifulSoup

PROJECT_PATTERNS={
    "waterpoint": re.compile(r"\bWaterpoint\b",re.I),
    "mizuki-park": re.compile(r"\bMizuki Park\b",re.I),
    "izumi-city": re.compile(r"\bIzumi City\b",re.I),
    "akari-city": re.compile(r"\bAkari City\b",re.I),
}

def parse_article(html: str, source_url: str, fetched_at: str):
    soup=BeautifulSoup(html,"lxml")
    title=(soup.find("h1").get_text(" ",strip=True) if soup.find("h1") else (soup.title.get_text(" ",strip=True) if soup.title else "Nam Long update"))
    text=" ".join(soup.stripped_strings)

    date=None
    m=re.search(r"\b([0-3]?\d)[/-]([01]?\d)[/-](20\d{2})\b",text)
    if m:
        date=f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    project_ids=[pid for pid,p in PROJECT_PATTERNS.items() if p.search(text)]
    tags=[]
    for tag,pat in [
        ("launch",r"mở bán|khởi động kinh doanh|ra mắt|giới thiệu phân khu"),
        ("sales",r"hấp thụ|được thị trường đón nhận|sold|bán"),
        ("handover",r"bàn giao|nhận sổ hồng|handover"),
        ("project-update",r"phân khu|dự án|khu đô thị"),
    ]:
        if re.search(pat,text,re.I):
            tags.append(tag)

    facts=[]
    m_units=re.search(r"(?:toàn bộ\s+)?(?:hơn\s+)?([\d.,]+)\s+sản phẩm[^\.]{0,100}?(?:tỷ lệ hấp thụ\s*)?100%",text,re.I)
    if m_units:
        facts.append({"type":"developer-stated-sales","units":int(re.sub(r"\D","",m_units.group(1))),"absorption_rate":1.0})
    m_cert=re.search(r"(\d{1,3})%\s+hộ\s+đã\s+nhận\s+sổ\s+hồng",text,re.I)
    if m_cert:
        facts.append({"type":"certificate-progress","household_pct":int(m_cert.group(1))/100})

    return {
        "title":title,
        "published_date":date,
        "project_ids":project_ids,
        "tags":tags,
        "facts":facts,
        "source_url":source_url,
        "fetched_at":fetched_at,
    }
