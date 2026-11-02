#!/usr/bin/env python3
"""Independently verify publisher product labels, never infer price/ASP.

This is a source availability and product taxonomy gate, not a price scraper.
Source URLs must belong to approved developer domains and have project-specific
heading plus exact product labels within the page.
"""
from __future__ import annotations
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import requests
from bs4 import BeautifulSoup
from market_landed_source_watch import permitted, MAX_BYTES, HEADERS

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/market-landed-product-scopes.json"
PROJECTS=ROOT/"data/mock/market/projects.json"
OUTPUT=ROOT/"data/state/market-landed-product-coverage.json"

def fold(value):
    value=unicodedata.normalize("NFD", str(value or "").lower().replace("đ","d"))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(c for c in value if not unicodedata.combining(c))).split())

def has_phrase(body, term):
    return bool(fold(term)) and " "+fold(term)+" " in " "+fold(body)+" "

def evidence(html, target):
    soup=BeautifulSoup(html,"lxml")
    for node in soup(["script","style","nav","footer","noscript"]):
        node.decompose()
    main=soup.find("main") or soup.find("article") or soup.body or soup
    headlines=[h.get_text(" ",strip=True) for h in main.find_all(["h1","h2"],limit=12)]
    if not any(has_phrase(h,target["expected_headline"]) for h in headlines):
        return None, "project-title-not-confirmed"
    text=main.get_text(" ",strip=True)
    if len(text)<120:
        return None, "insufficient-source-body"
    return {p["id"]:has_phrase(text,p["source_phrase"]) for p in target["product_types"]}, "source-checked"

def inspect(target, project, session, checked_at):
    url=target["source_url"]
    host=target["allowed_host"]
    row={"source_id":target["id"],"project_id":target["project_id"],
         "subproject_name":target["subproject_name"],"source_url":url,
         "checked_at":checked_at,"status":"not-checked","product_labels":[],
         "candidate_prices":0,"published_prices":0}
    if not permitted(url,host):
        row["status"]="unapproved-source-host"
        return row
    if "landed" not in project.get("segment_ids",[]):
        row["status"]="not-landed-project"
        return row
    try:
        response=session.get(url,headers=HEADERS,timeout=16,allow_redirects=True,stream=True)
        if not permitted(response.url,host):
            row["status"]="untrusted-redirect"
            return row
        row["http_status"]=response.status_code
        if response.status_code!=200:
            row["status"]="access-unavailable"
            return row
        raw=response.raw.read(MAX_BYTES+1,decode_content=True)
        if len(raw)>MAX_BYTES:
            row["status"]="oversize"
            return row
        verified,status=evidence(raw.decode(response.encoding or "utf-8",errors="replace"),target)
        row["status"]=status
        for p in target["product_types"]:
            row["product_labels"].append({
                "id":p["id"],"label":p["label"],"source_phrase":p["source_phrase"],
                "source_verified":bool(verified and verified.get(p["id"])),
                "price_status":"no-source-verified-dated-offer",
            })
    except requests.RequestException as exc:
        row["status"]="network-error"
        row["error_class"]=type(exc).__name__
    return row

def run(config,registry,session,checked_at):
    projects={p["id"]:p for p in registry.get("data",[])}
    seen=set()
    rows=[]
    for target in config.get("sources",[]):
        if target["id"] in seen or target["project_id"] not in projects:
            raise ValueError("duplicate-or-unknown-product-source")
        seen.add(target["id"])
        rows.append(inspect(target,projects[target["project_id"]],session,checked_at))
    if not rows:
        raise ValueError("empty-product-source-registry")
    return {
        "schema_version":1,"generated_at":checked_at,
        "scope":"official-product-labels-only-not-developer-price-or-transactions",
        "sources_checked":len(rows),
        "source_pages_available":sum(row["status"]=="source-checked" for row in rows),
        "product_types_catalogued":sum(len(t["product_types"]) for t in config["sources"]),
        "product_types_verified":sum(p["source_verified"] for row in rows for p in row["product_labels"]),
        "price_records_published":0,"sources":rows
    }

def main():
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    registry=json.loads(PROJECTS.read_text(encoding="utf-8"))
    result=run(config,registry,requests.Session(),
               datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Landed products: {result['product_types_verified']}/{result['product_types_catalogued']} labels verified, no price published")

if __name__=="__main__":
    main()
