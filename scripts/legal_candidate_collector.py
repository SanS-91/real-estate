#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
CANONICAL=ROOT/"data/mock/legal/documents.json"
TOPICS=ROOT/"data/mock/legal/topics.json"
AGENCIES=ROOT/"data/mock/core/agencies.json"
WATCH=ROOT/"data/candidate/registry/watch-report.json"
CAND=ROOT/"data/candidate/legal/documents.json"
REPORT=ROOT/"data/candidate/legal/legal-candidate-report.json"
HEADERS={"User-Agent":"VietnamRealEstateMarketIntelligence/1.0 (+GitHub Actions legal candidate collector)"}

def load(p,default=None):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else default

def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def norm(s): return re.sub(r"\s+"," ",str(s or "")).strip()

def slug(s):
    s=s.lower()
    s=re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s[:100]

def text_of(html):
    soup=BeautifulSoup(html,"lxml")
    for t in soup(["script","style","noscript"]): t.decompose()
    return soup,norm(soup.get_text(" ",strip=True))

def find_date(text,label_patterns):
    for label in label_patterns:
        m=re.search(label+r"\s*[:\-]?\s*([0-3]?\d[/-][01]?\d[/-]20\d{2})",text,re.I)
        if m:
            d,mn,y=re.split(r"[/-]",m.group(1))
            return f"{int(y):04d}-{int(mn):02d}-{int(d):02d}"
    return None

def document_number(text):
    patterns=[
      r"\b\d{1,4}/20\d{2}/QH\d+\b",
      r"\b\d{1,4}/20\d{2}/NĐ-CP\b",
      r"\b\d{1,4}/20\d{2}/ND-CP\b",
      r"\b\d{1,4}/20\d{2}/TT-[A-ZÀ-Ỹ0-9Đ-]+\b",
      r"\b\d{1,4}/20\d{2}/QĐ-[A-ZÀ-Ỹ0-9Đ-]+\b",
      r"\b\d{1,4}/20\d{2}/NQ-[A-ZÀ-Ỹ0-9Đ-]+\b",
    ]
    for p in patterns:
        m=re.search(p,text,re.I)
        if m: return m.group(0).upper().replace("ND-CP","NĐ-CP")
    return None

def document_type(number,title):
    n=(number or "").upper(); t=(title or "").lower()
    if "/QH" in n or t.startswith("luật"): return "law"
    if "/NĐ-CP" in n or t.startswith("nghị định"): return "decree"
    if "/TT-" in n or t.startswith("thông tư"): return "circular"
    if "/QĐ-" in n or t.startswith("quyết định"): return "decision"
    if "/NQ-" in n or t.startswith("nghị quyết"): return "resolution"
    return "other"

def agency_ids(text):
    tl=text.lower()
    rules=[
      ("national-assembly",["quốc hội","national assembly"]),
      ("government",["chính phủ","government"]),
      ("ministry-construction",["bộ xây dựng","ministry of construction"]),
      ("ministry-finance",["bộ tài chính","ministry of finance"]),
      ("hcmc-peoples-committee",["ủy ban nhân dân thành phố hồ chí minh","ubnd tp.hcm","hcmc people"]),
    ]
    return [aid for aid,words in rules if any(w in tl for w in words)][:1]

def topic_ids(title,text):
    hay=(title+" "+text[:5000]).lower()
    rules={
      "land":["đất đai","giá đất","tiền sử dụng đất","tiền thuê đất"],
      "housing":["nhà ở","nhà ở xã hội"],
      "real-estate-business":["kinh doanh bất động sản","môi giới bất động sản"],
      "planning":["quy hoạch","kế hoạch sử dụng đất"],
      "construction":["xây dựng","nghiệm thu","giấy phép xây dựng"],
      "investment":["đầu tư","chủ trương đầu tư"],
      "tax":["thuế","lệ phí"],
      "finance":["tín dụng","bảo lãnh","thanh toán","tài chính"],
    }
    return [tid for tid,kws in rules.items() if any(k in hay for k in kws)]

def title_from(soup,text,number):
    h=soup.find("h1")
    title=norm(h.get_text(" ",strip=True)) if h else ""
    if not title:
        title=norm(soup.title.get_text(" ",strip=True)) if soup.title else ""
    if number and title.upper().startswith(number.upper()):
        title=norm(title[len(number):].lstrip(" :-–"))
    if not title:
        title=(number or "Official legal document")
    return title[:500]

def parse(html,url,fetched_at):
    soup,text=text_of(html)
    num=document_number(text)
    title=title_from(soup,text,num)
    issued=find_date(text,[r"ngày ban hành",r"ban hành ngày",r"issued date"])
    effective=find_date(text,[r"ngày có hiệu lực",r"ngày hiệu lực",r"effective date"])
    agencies=agency_ids(text)
    topics=topic_ids(title,text)
    status="draft" if "dự thảo" in title.lower() else ("effective" if effective and effective <= datetime.now().date().isoformat() else "issued")
    return {
      "document_number":num,
      "title":title,
      "document_type":document_type(num,title),
      "status":status,
      "agency_ids":agencies,
      "scope_type":"national" if not agencies or agencies[0]!="hcmc-peoples-committee" else "local",
      "region_ids":["hcmc"] if agencies==["hcmc-peoples-committee"] else [],
      "topic_ids":topics,
      "issued_date":issued,
      "effective_date":effective,
      "official_url":url,
      "primary_source_id":"gov-vietnam-legal-documents",
      "collector_provenance":{"capture_mode":"official-page-parser","fetched_at":fetched_at,"review_required":True}
    }

def identity(row):
    return (str(row.get("document_number") or "").upper(), row.get("official_url"))

def candidate_id(row):
    base=row.get("document_number") or Path(urlparse(row["official_url"]).path).name or "legal-document"
    return "candidate-legal-"+slug(base)

def validate(row):
    issues=[]
    for f in ["document_number","title","document_type","official_url"]:
        if not row.get(f): issues.append("missing "+f)
    if not row.get("agency_ids"): issues.append("agency requires review")
    if not row.get("topic_ids"): issues.append("topic requires review")
    return issues

def collect_urls(args):
    urls=list(args.url or [])
    if args.from_watch and WATCH.exists():
        w=load(WATCH,{"discovery_links":[]})
        urls += [x["url"] for x in w.get("discovery_links",[]) if x.get("module")=="legal" and x.get("new_since_previous_check")]
    out=[]; seen=set()
    for u in urls:
        if u and u not in seen: seen.add(u); out.append(u)
    return out

def fetch(url):
    r=requests.get(url,headers=HEADERS,timeout=20,allow_redirects=True)
    r.raise_for_status()
    return r.url,r.text,datetime.now(timezone.utc).isoformat()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",action="append",default=[])
    ap.add_argument("--from-watch",action="store_true")
    ap.add_argument("--fixture")
    ap.add_argument("--fixture-url",default="https://vanban.chinhphu.vn/?docid=fixture&pageid=27160")
    args=ap.parse_args()

    canonical=load(CANONICAL,{"data":[]}).get("data",[])
    by_num={str(x.get("document_number") or "").upper():x for x in canonical if x.get("document_number")}
    by_url={x.get("official_url"):x for x in canonical if x.get("official_url")}
    rows=[]; reports=[]

    inputs=[]
    if args.fixture:
        inputs=[(args.fixture_url,Path(args.fixture).read_text(encoding="utf-8"),datetime.now(timezone.utc).isoformat())]
    else:
        for url in collect_urls(args):
            try:
                inputs.append(fetch(url))
            except Exception as e:
                reports.append({"url":url,"status":"fetch-error","error":str(e)[:300]})

    for final_url,html,fetched_at in inputs:
        row=parse(html,final_url,fetched_at)
        issues=validate(row)
        prev=(by_num.get(str(row.get("document_number") or "").upper()) or by_url.get(row.get("official_url")))
        if prev:
            state="unchanged" if all(prev.get(k)==row.get(k) for k in ["document_number","title","issued_date","effective_date","official_url"]) else "existing-review"
        else:
            state="new"
        if state=="new":
            row["id"]=candidate_id(row)
            row["review_issues"]=issues
            rows.append(row)
        reports.append({"url":final_url,"status":"parsed","decision":state,"document_number":row.get("document_number"),"review_issues":issues})

    payload={"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"candidate_only":True,"record_count":len(rows),"data":rows}
    report={"schema_version":1,"generated_at":payload["generated_at"],"production_written":False,"candidate_count":len(rows),"results":reports}
    dump(CAND,payload); dump(REPORT,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
