#!/usr/bin/env python3
"""Read-only extraction of THIRD-PARTY Izumi pricing/policy candidates.

This is a candidate-only price watch. Never publish to Product Benchmark price
history, sales-policy-readiness, or calculated Net Price/PV.
"""
from __future__ import annotations
import argparse,hashlib,json,re,requests
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data/state/market-dealer-commercial-candidates.json"
PRICE_URL="https://batdongsanhpr.com/tin-tuc/gia-izumi-canaria-thang-10-2026-nha-pho-vuon-tu-8-55-ty/"
POLICY_URL="https://batdongsanhpr.com/chinh-sach-ban-hang-izumi-canaria-tb143-den-31-12-2026/"
ALLOWED=("batdongsanhpr.com","www.batdongsanhpr.com")
PRODUCTS={("garden-townhouse","Zone 1"):re.compile(r"nhà phố vườn\s*zone\s*1",re.I),
          ("garden-townhouse","Zone 2"):re.compile(r"nhà phố vườn\s*zone\s*2",re.I),
          ("garden-townhouse","Zone 3"):re.compile(r"nhà phố vườn\s*zone\s*3",re.I),
          ("semidetached-villa",None):re.compile(r"biệt thự song lập",re.I)}
AMOUNT=re.compile(r"\b(\d{1,3}(?:[.,]\d{1,2})?)\s*tỷ(?:\s*đồng)?\b",re.I)

def fetch(url, getter=None):
    if urlsplit(url).hostname not in ALLOWED:raise ValueError("Unapproved commercial publisher")
    try:
        r=getter(url) if getter else requests.get(url,timeout=15,headers={"User-Agent":"RealEstateMarketIntelligence/1.0 (candidate source audit)"})
        parsed=urlsplit(getattr(r,"url",url))
        if parsed.scheme!="https" or parsed.hostname not in ALLOWED:
            return {"status":"untrusted-redirect","text":None,"http_status":getattr(r,"status_code",None)}
        if r.status_code!=200:return {"status":"blocked" if r.status_code in (401,403,429) else "http-error",
                                      "text":None,"http_status":r.status_code}
        body=getattr(r,"text","")
        if len(body)<100:return {"status":"empty-document","text":None,"http_status":200}
        return {"status":"fetched","text":body,"http_status":200}
    except requests.RequestException:
        return {"status":"unavailable","text":None,"http_status":None}

def extract_price_rows(html):
    soup=BeautifulSoup(html,"html.parser")
    candidates=[]
    # Match only a source table row with an explicitly named product/zone and
    # price in the same row: never mix the cheapest unit and an unrelated area.
    seen=set()
    for tr in soup.select("tr"):
        tds=[re.sub(r"\s+"," ",td.get_text(" ",strip=True)) for td in tr.find_all(["td","th"])]
        if len(tds)<2:continue
        name=tds[0]
        for key,pattern in PRODUCTS.items():
            if key in seen or not pattern.search(name):continue
            priced=[cell for cell in tds[1:] if AMOUNT.search(cell)]
            if not priced:continue
            # Prefer the rightmost explicit 'tỷ' quote, not any unrelated
            # payment example outside the price table.
            matches=AMOUNT.findall(priced[-1])
            if len(matches)!=1:continue
            amount=float(matches[0].replace(",","."))
            if amount<=0 or amount>200:continue
            candidates.append({"project_id":"izumi-city","subproject":"Izumi Canaria",
               "product_type":key[0],"zone":key[1],"reported_start_price_vnd":round(amount*1e9),
               "price_unit":"VND/unit","source_url":PRICE_URL,
               "price_basis":"broker-reported-starting-list-price-not-specific-unit",
               "original_signed_price_sheet_verified":False,
               "eligible_for_fs_asp":False,"eligible_for_net_price":False,
               "eligible_for_pv":False})
            seen.add(key)
    # Some publisher articles render pricing as paragraphs/cards rather than
    # literal HTML table rows. Scan only a named *price-list* section and
    # associate each named product/zone with its FIRST nearby 'tỷ' amount.
    if len(candidates)<len(PRODUCTS):
        full=re.sub(r"\\s+"," ",soup.get_text(" ",strip=True))
        markers=list(re.finditer(r"(?:giá niêm yết theo bảng tính|bảng tính giá.{0,55}tháng 10/2026)",full,re.I))
        if markers:
            text=full[markers[0].start():markers[0].start()+2600]
            for key,pattern in PRODUCTS.items():
                if key in seen:continue
                for m in pattern.finditer(text):
                    # Product must be followed by a quote before the next
                    # unrelated product row, and must not be an example discount.
                    ahead=text[m.end():m.end()+220]
                    amount_match=AMOUNT.search(ahead)
                    if not amount_match:continue
                    prior=text[max(0,m.start()-60):m.start()].lower()
                    if "ví dụ" in prior and "giá" in prior:continue
                    amount=float(amount_match.group(1).replace(",","."))
                    if not 5<=amount<=200:continue
                    candidates.append({"project_id":"izumi-city","subproject":"Izumi Canaria",
                       "product_type":key[0],"zone":key[1],"reported_start_price_vnd":round(amount*1e9),
                       "price_unit":"VND/unit","source_url":PRICE_URL,
                       "price_basis":"broker-reported-starting-list-price-not-specific-unit",
                       "original_signed_price_sheet_verified":False,
                       "eligible_for_fs_asp":False,"eligible_for_net_price":False,
                       "eligible_for_pv":False})
                    seen.add(key)
                    break
    return candidates

def extract_policy_alert(html):
    soup=BeautifulSoup(html,"html.parser")
    for script in soup(["script","style","noscript"]):script.decompose()
    body=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
    replacement=bool(re.search(r"TB153.{0,190}thay.{0,110}TB143",body,re.I))
    return {"reported_notice_id":"TB153/2026/DNWF/TB" if replacement else None,
      "reported_supersedes":"TB143/2026/DNWF/TB" if replacement else None,
      "supersession_detected":replacement,"source_url":POLICY_URL,
      "signed_document_verified":False,"discount_terms_verified":False,
      "status":"third-party-policy-alert-only" if replacement else "not-confirmed-on-source"}

def build(now=None,getter=None):
    now=now or datetime.now(timezone.utc)
    price=fetch(PRICE_URL,getter)
    policy=fetch(POLICY_URL,getter)
    leads=extract_price_rows(price["text"]) if price["text"] else []
    alert=extract_policy_alert(policy["text"]) if policy["text"] else None
    priceSoup=BeautifulSoup(price["text"] or "", "html.parser")
    readable=re.sub(r"\\s+"," ",priceSoup.get_text(" ",strip=True))
    diagnostics={"price_html_length":len(price["text"] or ""),
                 "visible_text_length":len(readable),
                 "html_table_rows":len(priceSoup.select("tr")),
                 "has_table_price_heading":bool(re.search(r"giá niêm yết.{0,35}bảng tính",readable,re.I)),
                 "has_zone1_label":bool(re.search(r"nhà phố vườn\\s*zone\\s*1",readable,re.I)),
                 "has_zone2_label":bool(re.search(r"nhà phố vườn\\s*zone\\s*2",readable,re.I)),
                 "has_zone3_label":bool(re.search(r"nhà phố vườn\\s*zone\\s*3",readable,re.I)),
                 "has_price_855":bool(re.search(r"8[,.]55\\s*tỷ",readable,re.I)),
                 "html_title":(priceSoup.title.get_text(" ",strip=True)[:110] if priceSoup.title else None),
                 "table_first_cell_labels":[tr.find_all(["td","th"])[0].get_text(" ",strip=True)[:65]
                    for tr in priceSoup.select("tr")[:8] if tr.find_all(["td","th"])],
                 "has_izumi_canaria":bool(re.search(r"Izumi\\s*Canaria",readable,re.I))}
    digest=hashlib.sha256(json.dumps([leads,alert],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    return {"schema_version":1,"checked_at":now.isoformat(),
      "source_type":"third-party-broker-candidate-only",
      "price_page_status":price["status"],"policy_page_status":policy["status"],
      "source_page_http_statuses":{"price":price["http_status"],"policy":policy["http_status"]},
      "source_revision":digest,"price_parser_diagnostics":diagnostics,
      "price_table_records_recognized":len(leads),
      "expected_price_groups":4,"completeness":"reviewable-full-table" if len(leads)==4 else "partial-or-unavailable",
      "price_candidates":leads,"policy_candidate":alert,
      "auto_promoted_prices":0,"approved_payment_schemes":0,"net_price_pv_published":False,
      "needs_primary_document_review":True,
      "notes":"Page accessibility and parsing success do not verify signed TB153, unit-specific price or discount eligibility. Never copy these candidates into approved FS data."}

def main():
    a=argparse.ArgumentParser();a.add_argument("--output",default=str(OUT));args=a.parse_args()
    output=build();dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":output["completeness"],"prices":output["price_table_records_recognized"],
                     "price_source":output["price_page_status"],"policy_source":output["policy_page_status"]},ensure_ascii=False))

if __name__=="__main__":main()
