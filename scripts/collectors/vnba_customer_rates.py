from __future__ import annotations
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
SOURCE_ID = "vnba"
MONTHS={"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
def _num(raw): return float(raw.strip().replace(",",".")) if raw is not None else None
def _compact(text): return re.sub(r"\s+"," ",text or " ").strip()
def _period(text):
    m=re.search(r"interest\s+rate\s+developments\s+applied\s+by\s+credit\s+institutions\s+in\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})",text,re.I)
    return f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}" if m else None
def _published_at(soup,text):
    for attrs in ({"property":"article:published_time"},{"name":"date"},{"name":"publish-date"}):
        tag=soup.find("meta",attrs=attrs)
        if tag and tag.get("content"):
            m=re.search(r"(20\d{2})-(\d{2})-(\d{2})",tag["content"])
            if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m=re.search(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b",text)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None
def parse_vnba_customer_rates(html,source_url,fetched_at):
    soup=BeautifulSoup(html,"lxml"); text=_compact(" ".join(soup.stripped_strings)); period=_period(text)
    if not period: return []
    dep=re.search(r"(?:terms?\s+between|terms?\s+from)\s+six\s+months?\s+(?:and|to)\s+12\s+months?[^.]{0,180}?(?:rates?\s+averaged|offered|provided|at)\s+([\d.,]+)\s*%\s*(?:to|-|–|—)\s*([\d.,]+)\s*%",text,re.I|re.S)
    lend=re.search(r"(?:VND\s+Lending|average\s+lending\s+interest\s+rates?)[^.]{0,260}?(?:range\s+of|within\s+the\s+range\s+of|from)?\s*([\d.,]+)\s*%\s*(?:to|-|–|—)\s*([\d.,]+)\s*%",text,re.I|re.S)
    priority=re.search(r"(?:priority\s+sectors?|priority\s+sectors?\s+and\s+areas?)[^.]{0,180}?(?:averaged|around|at)\s+([\d.,]+)\s*%",text,re.I|re.S)
    common={"period":period,"period_type":"month","unit":"percent-per-year","source_id":SOURCE_ID,"source_url":source_url,"published_at":_published_at(soup,text),"fetched_at":fetched_at,"evidence_status":"reported"}
    out=[]
    if dep:
        lo,hi=_num(dep.group(1)),_num(dep.group(2)); out += [{**common,"indicator_id":"deposit-rate-vnd-6-12m-low","value":lo,"methodology_note":"VNBA report citing SBV; lower bound of 6–12M VND deposit-rate range. Fallback evidence only."},{**common,"indicator_id":"deposit-rate-vnd-6-12m-high","value":hi,"methodology_note":"VNBA report citing SBV; upper bound of 6–12M VND deposit-rate range. Fallback evidence only."}]
    if lend:
        lo,hi=_num(lend.group(1)),_num(lend.group(2)); out += [{**common,"indicator_id":"lending-rate-vnd-average-low","value":lo,"methodology_note":"VNBA report citing SBV; lower bound of average VND lending-rate range. Fallback evidence only."},{**common,"indicator_id":"lending-rate-vnd-average-high","value":hi,"methodology_note":"VNBA report citing SBV; upper bound of average VND lending-rate range. Fallback evidence only."}]
    if priority: out.append({**common,"indicator_id":"priority-short-term-lending-rate-vnd","value":_num(priority.group(1)),"methodology_note":"VNBA report citing SBV; average short-term VND lending rate for priority sectors. Fallback evidence only."})
    return out
def _month_key(title):
    m=re.search(r"\bin\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})",title,re.I)
    return int(m.group(2))*100+MONTHS[m.group(1).lower()] if m else 0
def discover_vnba_customer_rates_url(html,landing_url):
    soup=BeautifulSoup(html,"lxml"); ranked=[]
    for idx,a in enumerate(soup.find_all("a",href=True)):
        title=_compact(" ".join(a.stripped_strings)); href=(a.get("href") or "").strip()
        if not href or not re.search(r"interest\s+rate\s+developments\s+applied\s+by\s+credit\s+institutions",title,re.I): continue
        url=urljoin(landing_url,href)
        if "/hashtag/" in urlparse(url).path.lower(): continue
        ranked.append((_month_key(title),-idx,url))
    if not ranked: return None
    ranked.sort(reverse=True); return ranked[0][2]
