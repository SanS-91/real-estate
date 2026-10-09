"""Probe pinned CafeLand single-listing evidence without inferring price changes.

HTTP access is not proof of data quality. This health-only monitor never writes
secondary price records, source publication dates, project ASP or historical
price observations. Bad/mismatched project and product labels require review.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"data/mock/market/secondary-listing-evidence.json"
STATE=ROOT/"data/state/secondary-listing-source-health.json"
REPORT=ROOT/"data/candidate/market/secondary-listing-probe-report.json"
MAX_BYTES=5_000_000
TIMEOUT=16
HEADERS={"User-Agent":"MarketIntelligenceResearchBot/1.0 (public source health review)",
         "Accept":"text/html,application/xhtml+xml","Accept-Language":"vi-VN,vi;q=0.9"}


def html_text(raw):
    soup=BeautifulSoup(raw,"lxml")
    for x in soup(["script","style","noscript"]):
        x.decompose()
    return re.sub(r"\s+"," ",soup.get_text(" ",strip=True))


def classify(row, html):
    t=html_text(html)
    if len(t)<100 or re.search(r"captcha|checking your browser|verify you are human|just a moment",t[:800],re.I):
        return {"status":"blocked-or-empty-page"}
    src_date=row["source_publication_date"].split("-")
    quoted=row["evidence"]
    matches={
        "project_label": any(token.lower() in t.lower() for token in ({
            "izumi-city":["Izumi City"],"essensia-parkway":["Essensia Parkway"],
            "the-9-stellars":["The 9 Stellars"]}.get(row["project_id"],[]))),
        "listing_id":row["listing_id"] in t,
        "published_date": (f"{src_date[2]}-{src_date[1]}-{src_date[0]}" in t),
        "advertised_unit_price":quoted["price"].lower().replace(" ","") in t.lower().replace(" ",""),
        "advertised_area":quoted["area"].lower().replace(" ","") in t.lower().replace(" ",""),
    }
    # This is a fresh access probe for an *existing listing*, not a new price date.
    return {"status":"source-evidence-visible" if all(matches.values()) else "reachable-review-required",
            "evidence_fields":matches}


def fetch(row, session):
    uri=urlsplit(row["source_url"])
    if (uri.scheme,uri.hostname,uri.query,uri.fragment)!=("https","nhadat.cafeland.vn","",""):
        return {"status":"invalid-source-url"}
    try:
        response=session.get(row["source_url"],headers=HEADERS,timeout=TIMEOUT,stream=True,allow_redirects=True)
        code=response.status_code
        host=urlsplit(response.url).hostname
        result={"http_status":code,"final_host":host}
        if host!="nhadat.cafeland.vn":
            response.close()
            return dict(result,status="redirect-off-source")
        if code in (401,403,429):
            response.close()
            return dict(result,status="blocked")
        if code!=200:
            response.close()
            return dict(result,status="http-error")
        if "html" not in response.headers.get("Content-Type","").lower():
            response.close()
            return dict(result,status="non-html")
        chunks=[];size=0
        for chunk in response.iter_content(chunk_size=32768):
            size+=len(chunk)
            if size>MAX_BYTES:
                response.close()
                return dict(result,status="too-large")
            chunks.append(chunk)
        response.close()
        raw=b"".join(chunks).decode(response.encoding or "utf-8",errors="replace")
        return dict(result,**classify(row,raw))
    except requests.RequestException as e:
        return {"status":"fetch-error","error_type":e.__class__.__name__}


def probe(rows,session,fetcher=fetch):
    results=[]
    for row in rows:
        result={"id":row["id"],"project_id":row["project_id"],
                "source_publication_date":row["source_publication_date"],
                **fetcher(row,session)}
        results.append(result)
    return results


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--date",default=datetime.now(timezone.utc).date().isoformat())
    args=parser.parse_args()
    rows=json.loads(EVIDENCE.read_text(encoding="utf-8"))["data"]
    checks=probe(rows,requests.Session())
    counts={k:sum(r["status"]==k for r in checks) for k in sorted({r["status"] for r in checks})}
    now=datetime.now(timezone.utc).isoformat()
    output={"schema_version":1,"generated_at":now,"source_check_date":args.date,
            "targets_checked":len(checks),"new_history_candidates":0,
            "production_written":False,"counts":counts,"checks":checks,
            "note":"Date here is a check date, NOT a price observation period. An old listing cannot become a new historical price."}
    for path in (STATE,REPORT):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"targets":len(checks),"new_candidates":0,"counts":counts},ensure_ascii=False))

if __name__=="__main__":
    main()
