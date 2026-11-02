#!/usr/bin/env python3
"""Landed individual asking-offer monitor, fail closed.

Public NhaTot sale detail links only. A row must show the exact project on
its OWN detail page, landed property type, land area, total asking amount,
matching per-sqm asking amount and absolute publisher update date.
Two independent GitHub checks >=60m apart must agree before release.
No project price range, median, deal, developer ASP or downpayment-derived price.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/market-landed-unit-listing-targets.json"
REGISTRY=ROOT/"data/mock/market/projects.json"
STATE=ROOT/"data/state/market-landed-unit-verification.json"
OUT=ROOT/"data/mock/market/verified-landed-unit-listings.json"
REPORT=ROOT/"data/state/market-landed-unit-source-health.json"
HOST="www.nhatot.com"
USER_AGENT="MarketIntelligenceResearchBot/1.0 (public source monitoring)"
MAX_BYTES=2_500_000
MAX_DETAIL_PER_PROJECT=10
PRODUCT_TYPES={
    "nha pho lien ke":"townhouse",
    "nha mat pho mat tien":"townhouse",
    "nha biet thu":"villa",
    "shophouse":"shophouse",
}
PRICE=re.compile(r"(?<!\d)(\d{1,3}(?:[,.]\d{1,3})?)\s*tỷ\b",re.I)
PER_SQM=re.compile(r"(?<!\d)(\d{1,3}(?:[,.]\d{1,3})?)\s*triệu\s*/\s*m[²2]",re.I)
AREA=re.compile(r"diện tích đất\s*:?\s*(\d+(?:[,.]\d+)?)\s*m[²2]",re.I)
PRODUCT=re.compile(r"loại hình\s*:?\s*(nhà phố liền kề|nhà mặt phố,?\s*mặt tiền|nhà biệt thự|shophouse)\b",re.I)
ABSOLUTE_DATE=re.compile(r"^\d{4}-\d{2}-\d{2}$")

def load(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback

def write(path, payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def fold(text):
    n=unicodedata.normalize("NFD",str(text or "").lower().replace("đ","d"))
    return re.sub(r"\s+"," ","".join(c for c in n if not unicodedata.combining(c))).strip()

def site_url(url, detail=False):
    p=urlsplit(url)
    if p.scheme!="https" or p.hostname not in {"www.nhatot.com","nhatot.com"}:
        return None
    if p.username or p.password or p.query or p.fragment:
        return None
    if detail:
        if not re.fullmatch(r"/mua-ban-(?:nha-dat|can-ho-chung-cu)-[^/]+/\d{7,12}\.htm",p.path):
            return None
    else:
        if not re.fullmatch(r"/mua-ban-du-an-[^/]+-pj\d{6,12}",p.path):
            return None
    return "https://www.nhatot.com"+p.path.rstrip("/")

def parse_publisher_date(soup, now):
    candidates=[]
    for attr,key in (("property","article:modified_time"),("itemprop","dateModified"),
                     ("name","dateModified"),("property","article:published_time")):
        tag=soup.find("meta",attrs={attr:key})
        if tag:
            candidates.append(tag.get("content",""))
    for tag in soup.find_all("time",datetime=True,limit=5):
        candidates.append(tag.get("datetime",""))
    accepted=[]
    for raw in candidates:
        d=raw[:10]
        if not ABSOLUTE_DATE.fullmatch(d):
            continue
        try:
            day=date.fromisoformat(d)
        except ValueError:
            continue
        if 0<=(now.date()-day).days<=45:
            accepted.append(d)
    return max(accepted,default=None)

def discover(html,catalog):
    if not site_url(catalog):
        return []
    soup=BeautifulSoup(html,"lxml")
    result=[]
    for node in soup.select("a[href]"):
        target=site_url(urljoin(catalog,node.get("href","")),detail=True)
        if target and target not in result:
            result.append(target)
    return result[:MAX_DETAIL_PER_PROJECT]

def parse_detail(html,url,project,now):
    if not site_url(url,detail=True):
        return None,"invalid-detail-url"
    soup=BeautifulSoup(html,"lxml")
    h1=soup.find("h1")
    if not h1:
        return None,"missing-listing-heading"
    heading=h1.get_text(" ",strip=True)
    for node in soup(["script","style","noscript","footer","nav"]):
        node.decompose()
    text=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
    pos=text.find(heading)
    if pos<0:
        return None,"missing-header-block"
    near=text[pos+len(heading):pos+len(heading)+480]
    # Never include the seller's marketing description; it may mention a
    # downpayment, old price, discount or unrelated project as a second offer.
    near=re.split(r"Cập nhật|Đặc điểm bất động sản|Mô tả chi tiết|Thông tin dự án",
                  near, maxsplit=1, flags=re.I)[0]
    # Source project card is a distinct listing attribute. A project named
    # solely in the marketing paragraph is not valid project attribution.
    project_match=re.search(r"Thông tin dự án\s+(.{0,110})",text,re.I)
    if not project_match or fold(project["name"]) not in fold(project_match.group(1)):
        return None,"project-not-on-listing-project-card"
    match=PRODUCT.search(text[pos:pos+4000])
    if not match:
        return None,"unclassified-landed-product"
    product=PRODUCT_TYPES.get(fold(match.group(1)).replace(",",""),None)
    if not product:
        return None,"wrong-product-type"
    size=AREA.search(text[pos:pos+4000])
    if not size:
        return None,"no-explicit-land-area"
    area=float(size.group(1).replace(",","."))
    if not 40<=area<=1500:
        return None,"implausible-land-area"
    # Read ask from listing HEADER, not the marketing body (where installment
    # or discounted amounts can be quoted without being the total price).
    prices=PRICE.findall(near)
    rates=PER_SQM.findall(near)
    if len(prices)!=1 or len(rates)!=1:
        return None,"ambiguous-or-missing-header-total-and-rate"
    total=int(round(float(prices[0].replace(",","."))*1_000_000_000))
    rate=int(round(float(rates[0].replace(",","."))*1_000_000))
    if not (1_000_000_000<=total<=250_000_000_000 and
            5_000_000<=rate<=1_000_000_000 and
            abs(total/area-rate)/rate<=0.025):
        return None,"price-area-rate-mismatch"
    when=parse_publisher_date(BeautifulSoup(html,"lxml"),now)
    if not when:
        return None,"absolute-publisher-update-date-unavailable"
    ident=re.search(r"/(\d{7,12})\.htm$",url)
    record={
       "source_id":"nhatot-vn","project_id":project["id"],
       "project_name":project["name"],"source_url":url,
       "listing_id":ident.group(1),"listing_title":heading[:160],
       "asset_type":"landed","product_type":product,
       "market_layer":"individual-listing-asking",
       "metric_type":"single-unit-asking-price-per-land-sqm",
       "listed_land_area_sqm":area,"listing_price_vnd":total,
       "value_vnd_per_land_m2":rate,"source_updated_date":when,
       "market_price_basis":"advertised-total-price-not-upfront-cash-to-pay",
       "subproject_id":None,
       "methodology_note":"Individual unverified asking offer; not a transaction, project ASP or primary developer price. Only explicit dated identical publisher checks can release.",
    }
    return record,"qualified-source-evidence"

def fetch(session,url,detail=False):
    if not site_url(url,detail=detail):
        return None,"invalid-url"
    try:
        response=session.get(url,headers={"User-Agent":USER_AGENT},
                             timeout=16,allow_redirects=True,stream=True)
        if not site_url(response.url,detail=detail):
            return None,"untrusted-redirect"
        if response.status_code!=200:
            return None,"http-"+str(response.status_code)
        raw=response.raw.read(MAX_BYTES+1,decode_content=True)
        if len(raw)>MAX_BYTES:
            return None,"oversize"
        return raw.decode(response.encoding or "utf-8",errors="replace"),"reachable"
    except requests.RequestException as err:
        return None,type(err).__name__

def fingerprint(row):
    fields=("source_id","project_id","listing_id","asset_type","product_type",
            "listed_land_area_sqm","listing_price_vnd","value_vnd_per_land_m2",
            "source_updated_date","source_url")
    payload=json.dumps([row.get(k) for k in fields],ensure_ascii=False,separators=(",",":"))
    return hashlib.sha256(payload.encode()).hexdigest()

def evaluate(old,existing,offers,now,run_id):
    proofs=dict(old.get("proofs",{}))
    previously={(x.get("source_id"),x.get("listing_id"),fingerprint(x)):x for x in existing}
    published=[]
    decisions=[]
    for row in offers:
        token=row["source_id"]+":"+row["listing_id"]
        digest=fingerprint(row)
        prior=proofs.get(token)
        prior_at=None
        try:
            if prior and prior.get("checked_at"):
                prior_at=datetime.fromisoformat(prior["checked_at"])
        except ValueError:
            pass
        same=bool(prior and prior.get("fingerprint")==digest and
            prior.get("run_id")!=run_id and prior_at and prior_at.tzinfo and
            timedelta(hours=1)<=now-prior_at<=timedelta(days=10))
        if (row["source_id"],row["listing_id"],digest) in previously:
            decisions.append({"listing_id":row["listing_id"],"decision":"already-recorded"})
            continue
        if same:
            published.append({
                **row,"id":"landed-nhatot-"+row["listing_id"]+"-"+digest[:12],
                "review_status":"automated-two-hosted-dated-checks",
                "verification_run_ids":[prior["run_id"],run_id],
                "verified_at":now.isoformat(),
            })
            decisions.append({"listing_id":row["listing_id"],"decision":"independent-dated-checks-matched"})
        else:
            decisions.append({"listing_id":row["listing_id"],"decision":"awaiting-independent-source-check"})
        proofs[token]={"fingerprint":digest,"checked_at":now.isoformat(),"run_id":run_id}
    return {"schema_version":1,"checked_at":now.isoformat(),"proofs":proofs},published,decisions

def run(config,projects,prior,existing,session,now,run_id):
    index={p["id"]:p for p in projects.get("data",[])}
    samples=[]
    rows=[]
    for target in config.get("targets",[]):
        pid=target["project_id"]
        project=index.get(pid)
        if not project or "landed" not in project.get("segment_ids",[]):
            raise ValueError("target is not an approved landed project")
        catalog=target["catalog_url"]
        listing_urls=[site_url(x,detail=True) for x in target.get("seed_urls",[])]
        if None in listing_urls or not site_url(catalog):
            raise ValueError("unsafe catalog or seed URL")
        listing_urls=list(dict.fromkeys(listing_urls))
        catalog_html,status=fetch(session,catalog)
        if catalog_html:
            listing_urls=list(dict.fromkeys(discover(catalog_html,catalog)+listing_urls))
        stats={"project_id":pid,"catalog_status":status,"urls_checked":0,
               "source_qualified":0,"reasons":{},
               "ads_with_absolute_source_date":0,
               "price_records_released":0}
        for url in listing_urls[:MAX_DETAIL_PER_PROJECT]:
            body,access=fetch(session,url,detail=True)
            stats["urls_checked"]+=1
            if body is None:
                reason=access
            else:
                row,reason=parse_detail(body,url,project,now)
                if row:
                    rows.append(row)
                    stats["source_qualified"]+=1
                    stats["ads_with_absolute_source_date"]+=1
            stats["reasons"][reason]=stats["reasons"].get(reason,0)+1
        samples.append(stats)
    new_state,promoted,decisions=evaluate(prior,existing.get("data",[]),rows,now,run_id)
    by_id={}
    for row in existing.get("data",[])+promoted:
        by_id[row["id"]]=row
    output={"schema_version":1,"collection_mode":"individual-dated-landed-asking-only",
            "record_count":len(by_id),"data":list(by_id.values())}
    report={"schema_version":1,"generated_at":now.isoformat(),
            "sources_checked":len(samples),"qualified_offers":len(rows),
            "released_new_individual_offers":len(promoted),
            "historical_verified_offers":output["record_count"],
            "candidates_with_missing_date_not_published":sum(
                x["reasons"].get("absolute-publisher-update-date-unavailable",0) for x in samples),
            "price_published_only_after_two_dated_checks":True,
            "no_market_asp_or_transactions":True,
            "sources":samples,"decisions":decisions[:30]}
    for item in samples:
        item["price_records_released"]=sum(x["project_id"]==item["project_id"] for x in promoted)
    return new_state,output,report

def main():
    cfg=load(CONFIG,{})
    projects=load(REGISTRY,{})
    previous=load(STATE,{"proofs":{}})
    published=load(OUT,{"data":[]})
    now=datetime.now(timezone.utc).replace(microsecond=0)
    run_id=os.getenv("GITHUB_RUN_ID") or "manual-"+now.isoformat()
    state,output,report=run(cfg,projects,previous,published,
                           requests.Session(),now,run_id)
    # An unreachable source cannot erase previously verified evidence.
    write(STATE,state)
    write(OUT,output)
    write(REPORT,report)
    print(json.dumps({k:report[k] for k in ("sources_checked","qualified_offers",
            "released_new_individual_offers","candidates_with_missing_date_not_published")},
        ensure_ascii=False))

if __name__=="__main__":
    main()
