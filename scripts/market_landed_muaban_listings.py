#!/usr/bin/env python3
"""Source-dated Muaban landed unit asking offers, strictly separate from apartments.

Project identity, land area, property type and absolute start/expiration dates
must be on the publisher's own detail page. Only two independent matching
GitHub-hosted checks at least one hour apart may publish an individual offer.
A crawler visit cannot renew an expired ad. Never construct developer ASP.
"""
from __future__ import annotations
import json
import os
import re
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit,urljoin
import requests
from bs4 import BeautifulSoup
from market_landed_unit_listings import evaluate,write

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/market-landed-muaban-targets.json"
REGISTRY=ROOT/"data/mock/market/projects.json"
STATE=ROOT/"data/state/market-landed-muaban-verification.json"
OUT=ROOT/"data/mock/market/verified-landed-muaban-listings.json"
HEALTH=ROOT/"data/state/market-landed-muaban-source-health.json"
HOST="muaban.net"
MAX_BYTES=3_000_000
MAX_LISTINGS=10
AGENT="MarketIntelligenceResearchBot/1.0 (public listings source verification)"
PRICE=re.compile(r"(?<!\d)(\d{1,3}(?:[.,]\d{1,3})?)\s*tỷ\b",re.I)
AREA=re.compile(r"(\d{2,4}(?:[,.]\d+)?)\s*m[²2]",re.I)
DATE_RX=r"(\d{2})/(\d{2})/(20\d{2})"
ID_RX=re.compile(r"-id(\d{7,12})$",re.I)
HEAD_RX=re.compile(r"chỉ từ|giá từ|bảng giá|giỏ hàng|tổng hợp nhiều căn|cho thuê",re.I)

def load(path,default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def safe_url(url,detail=False):
    z=urlsplit(str(url))
    if z.scheme!="https" or z.hostname not in ("muaban.net","www.muaban.net") or z.username or z.password or z.query or z.fragment or z.port not in (None,443):
        return None
    path=z.path.rstrip("/")
    if not re.fullmatch(r"/bat-dong-san/(?:ban-nha-[a-z0-9-]+|ban-biet-thu-villa-penthouse-[a-z0-9-]+)(?:/[a-z0-9-]+-id\d{7,12})?",path):
        return None
    is_detail=bool(ID_RX.search(path))
    if is_detail!=detail:
        return None
    return "https://muaban.net"+path

def date_value(raw):
    match=re.search(DATE_RX,raw or "")
    if not match:
        return None
    try:
        return date(int(match[3]),int(match[2]),int(match[1]))
    except ValueError:
        return None

def basic_value(block,label):
    rx=re.compile(r"(?:^|\s)"+re.escape(label)+
         r"\s*:\s*(.+?)(?=\s+(?:Loại hình nhà ở|Dự án|Diện tích đất|Diện tích sử dụng|Số phòng ngủ|Số phòng vệ sinh|Tổng số tầng|Giấy tờ pháp lý|Hướng cửa chính|Hướng ban công|Điểm nổi bật)\s*:|$)",re.I)
    matches=rx.findall(block)
    return matches[0].strip() if len(matches)==1 else None

def parse_detail(html,url,project,now,publisher_project_name=None):
    safe=safe_url(url,detail=True)
    if not safe:
        return None,"invalid-source-url"
    soup=BeautifulSoup(html,"lxml")
    for node in soup(["script","style","noscript","nav","footer"]):
        node.decompose()
    heading=soup.find("h1")
    if not heading:
        return None,"missing-detail-header"
    title=heading.get_text(" ",strip=True)
    if re.search(r"cho thuê|đất nền|căn hộ|nhà ở xã hội",title,re.I):
        return None,"wrong-property-or-rental"
    raw="\n".join(x.strip() for x in heading.next_elements if isinstance(x,str) and x.strip())[:22000]
    if "Thông tin chi tiết" not in raw or "Thông tin cơ bản" not in raw:
        return None,"missing-listing-detail"
    first=raw.split("Thông tin chi tiết",1)[0]
    # The heading can mention a DEPOSIT or a price incentive. The listing
    # source's own sale price starts AFTER the H1. Never count title amounts
    # as an additional header offer or use them as the total asking price.
    first_lines=first.splitlines()
    if not first_lines or first_lines[0].strip()!=title:
        return None,"unverifiable-heading-boundary"
    header_body="\n".join(first_lines[1:])[:1000]
    if re.search(r"giá từ|chỉ từ|giỏ hàng|nhiều căn",title,re.I):
        return None,"non-single-unit-sale-heading"
    if HEAD_RX.search(header_body[:700]):
        return None,"multiple-or-price-from-offer"
    prices=PRICE.findall(header_body)
    if len(prices)!=1:
        return None,"missing-or-ambiguous-header-total"
    total=int(round(float(prices[0].replace(",","."))*1_000_000_000))
    if re.search(r"chỉ đóng|chỉ thanh toán|trả trước|đóng trước|cọc|thanh toán ban đầu",title,re.I):
        title_amounts=PRICE.findall(title)
        if any(abs(float(v.replace(",","."))*1_000_000_000-total)/total < .025
               for v in title_amounts):
            return None,"header-total-matches-upfront-only-title"
    if not 1_000_000_000<=total<=250_000_000_000:
        return None,"implausible-sale-amount"
    description=raw.split("Thông tin chi tiết",1)[1].split("Thông tin cơ bản",1)[0]
    if re.search(r"\bgiỏ hàng\b|nhiều căn|tổng hợp căn",description,re.I):
        return None,"multiple-units-in-one-ad"
    other=re.findall(r"(?:giá(?:\s+bán|\s+sau\s+csbh)?|tổng\s+giá)\s*:\s*(\d+(?:[,.]\d+)?)\s*tỷ\b",description,re.I)
    if any(abs(float(x.replace(",","."))*1e9-total)/total>.025 for x in other):
        return None,"conflicting-total-price-in-description"
    basic=raw.split("Thông tin cơ bản",1)[1].split("Thông tin dự án",1)[0]
    flat=re.sub(r"\s+"," ",basic).strip()
    project_name=basic_value(flat,"Dự án")
    expected=publisher_project_name or project["name"]
    if not project_name or project_name.casefold()!=expected.casefold():
        return None,"project-not-explicit-in-basic-info"
    typ=basic_value(flat,"Loại hình nhà ở") or basic_value(flat,"Loại hình bất động sản")
    if not typ:
        return None,"unknown-product-type"
    if re.fullmatch(r"Nhà mặt tiền|Nhà phố liền kề|Nhà phố",typ,re.I):
        kind="townhouse"
    elif re.fullmatch(r"Nhà biệt thự|Biệt thự",typ,re.I):
        kind="villa"
    elif re.fullmatch(r"Shophouse|Nhà phố thương mại",typ,re.I):
        kind="shophouse"
    else:
        return None,"non-landed-or-ambiguous-product"
    a=basic_value(flat,"Diện tích đất")
    area=AREA.search(a or "")
    if not area:
        return None,"no-land-area"
    sqm=float(area[1].replace(",","."))
    if not 40<=sqm<=1500:
        return None,"implausible-land-area"
    def exact_date(label):
        matches=re.findall(re.escape(label)+r"\s*:?\s*"+DATE_RX,raw,re.I)
        if len(matches)!=1:
            return None
        try:
            return date(int(matches[0][2]),int(matches[0][1]),int(matches[0][0]))
        except ValueError:
            return None
    start=exact_date("Ngày bắt đầu")
    expiry=exact_date("Ngày hết hạn")
    if not start or not expiry or expiry<start:
        return None,"missing-or-conflicting-publisher-validity"
    local_day=now.astimezone(timezone(timedelta(hours=7))).date()
    if expiry<local_day:
        return None,"publisher-expired"
    if start>local_day:
        return None,"future-publisher-start"
    if (local_day-start).days>90:
        return None,"older-than-90-days"
    lid=ID_RX.search(safe).group(1)
    found=re.findall(r"Mã tin\s*:?\s*(\d{7,12})(?!\d)",raw,re.I)
    if len(found)!=1 or found[0]!=lid:
        return None,"listing-id-mismatch"
    rate=int(round(total/sqm))
    if not 5_000_000<=rate<=700_000_000:
        return None,"implausible-land-asking-rate"
    return {
        "source_id":"muaban-vn","source_url":safe,"listing_id":lid,
        "listing_title":title[:160],"project_id":project["id"],"project_name":project["name"],
        "asset_type":"landed","product_type":kind,
        "market_layer":"individual-listing-asking",
        "metric_type":"single-unit-asking-price-per-land-sqm",
        "listed_land_area_sqm":sqm,"listing_price_vnd":total,
        "value_vnd_per_land_m2":rate,"source_updated_date":start.isoformat(),
        "source_listed_date":start.isoformat(),"source_expiration_date":expiry.isoformat(),
        "source_date_basis":"publisher-start-not-relative-update",
        "market_price_basis":"total-advertised-not-first-payment",
        "subproject_id":None,
        "methodology_note":"Muaban individual asking offer only, valid from explicit publisher start to expiry; unit rate derives from asking total divided by land area, never project ASP."
    },"qualified-unexpired-landed-offer"

def discover(html,catalog,project_name=None,regional=False):
    if not safe_url(catalog):
        return []
    urls=[]
    for a in BeautifulSoup(html,"lxml").select("a[href]"):
        u=safe_url(urljoin(catalog,a.get("href","")),detail=True)
        if not u or u in urls:
            continue
        if regional and project_name:
            # Regional category pages contain dozens of unrelated projects.
            # Search only the link's OWN text/image/URL, not the whole page
            # (which can mention Waterpoint in an unrelated recommendation).
            title=" ".join([a.get_text(" ",strip=True),
                            str(a.get("title","")),
                            str(a.find("img").get("alt","") if a.find("img") else ""),
                            u])
            if not re.search(r"(?<![a-z])"+re.escape(project_name)+r"(?![a-z])",
                             title,re.I):
                continue
        urls.append(u)
    return urls[:MAX_LISTINGS]

def fetch(session,url,detail=False):
    if not safe_url(url,detail=detail):
        return None,"unsafe-url"
    try:
        resp=session.get(url,headers={"User-Agent":AGENT},timeout=16,
                         allow_redirects=True,stream=True)
        if not safe_url(resp.url,detail=detail):
            return None,"untrusted-redirect"
        if resp.status_code!=200:
            return None,"http-"+str(resp.status_code)
        raw=resp.raw.read(MAX_BYTES+1,decode_content=True)
        if len(raw)>MAX_BYTES:
            return None,"over-size"
        return raw.decode(resp.encoding or "utf-8",errors="replace"),"reachable"
    except requests.RequestException as exc:
        return None,type(exc).__name__

def run(config,registry,previous,already,session,now,run_id):
    by_id={p["id"]:p for p in registry.get("data",[])}
    candidates=[]
    statuses=[]
    for target in config.get("targets",[]):
        project=by_id.get(target["project_id"])
        if not project or "landed" not in project.get("segment_ids",[]):
            raise ValueError("unknown or non-landed project")
        catalog=target["catalog_url"]
        catalogs=list(dict.fromkeys([catalog]+target.get("catalog_urls",[])))
        if not catalogs or any(not safe_url(u) for u in catalogs) or any(not safe_url(u,detail=True) for u in target.get("seed_urls",[])):
            raise ValueError("unsafe approved source URL")
        urls=[]
        catalog_statuses=[]
        for catalog_url in catalogs[:3]:
            page,status=fetch(session,catalog_url)
            catalog_statuses.append({"url":catalog_url,"status":status})
            if page:urls.extend(discover(
                page,catalog_url,project_name=project["name"],
                regional=target.get("catalog_scope","").startswith("two-regional") or
                target.get("catalog_scope","").startswith("regional-broad")))
        status="reachable" if any(x["status"]=="reachable" for x in catalog_statuses) else catalog_statuses[0]["status"]
        urls=list(dict.fromkeys(urls+target.get("seed_urls",[])))
        result={"project_id":project["id"],"catalog_status":status,
                "catalog_scope":target.get("catalog_scope","publisher-project-category"),
                "catalogs":catalog_statuses,
                "detail_checked":0,"qualified":0,"reasons":{}}
        for url in urls[:MAX_LISTINGS]:
            body,state=fetch(session,url,True)
            if body:
                row,state=parse_detail(body,url,project,now,target.get("publisher_project_name"))
                if row:
                    candidates.append(row)
                    result["qualified"]+=1
            result["detail_checked"]+=1
            result["reasons"][state]=result["reasons"].get(state,0)+1
        statuses.append(result)
    new_state,new,decisions=evaluate(previous,already.get("data",[]),candidates,now,run_id)
    # Never release/retain an expired offer as currently live. Keep its history
    # but expiry must be checked at display time.
    # A previously published offer remains in history, but is CURRENT only
    # if the publisher page was directly rechecked and its full price/area/
    # validity evidence still matches. A changed price invalidates the old
    # offer immediately, not 48 hours later. Unreachable is also not live.
    observed={(x["source_id"],x["listing_id"]):x for x in candidates}
    compare_keys=("source_id","project_id","listing_id","product_type",
                  "listed_land_area_sqm","listing_price_vnd",
                  "value_vnd_per_land_m2","source_updated_date",
                  "source_listed_date","source_expiration_date","source_url")
    saved={}
    for record in already.get("data",[])+new:
        item=dict(record)
        matching=observed.get((item.get("source_id"),item.get("listing_id")))
        if matching and all(item.get(key)==matching.get(key) for key in compare_keys):
            item["last_source_verified_at"]=now.isoformat()
            item["source_status"]="confirmed-match"
        elif matching:
            item["source_status"]="changed-pending-verification"
        else:
            item["source_status"]="not-reconfirmed"
        if "last_source_verified_at" not in item:
            item["last_source_verified_at"]=item.get("verified_at")
        saved[item["id"]]=item
    out={"schema_version":1,"collection_mode":"dated-unexpired-individual-landed-asking-only",
         "record_count":len(saved),"data":list(saved.values())}
    health={"schema_version":1,"generated_at":now.isoformat(),
            "sources_checked":len(statuses),"qualified_offers":len(candidates),
            "published_new_offers":len(new),"historical_offers":len(saved),
            "no_project_asp_or_deals":True,"sources":statuses,"decisions":decisions[:40]}
    return new_state,out,health

def main():
    cfg=load(CONFIG,{})
    registry=load(REGISTRY,{})
    now=datetime.now(timezone.utc).replace(microsecond=0)
    prior=load(STATE,{"proofs":{}})
    saved=load(OUT,{"data":[]})
    state,out,health=run(cfg,registry,prior,saved,requests.Session(),
                         now,os.getenv("GITHUB_RUN_ID","manual-"+now.isoformat()))
    write(STATE,state)
    write(OUT,out)
    write(HEALTH,health)
    print("Muaban landed: qualified=%d, released=%d, historical=%d"%
          (health["qualified_offers"],health["published_new_offers"],out["record_count"]))

if __name__=="__main__":
    main()
