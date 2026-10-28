#!/usr/bin/env python3
"""Validate broker-reported unit-group starting-price leads and policy version changes.

This is a REVIEW QUEUE, never current official developer prices, project ASP,
contract net price, PV, or a date-series price observation. Only manual
source-document verification outside this pipeline may promote a lead.
"""
from __future__ import annotations
import argparse,hashlib,json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"data/mock/market/commercial-offer-leads.json"
SOURCES=ROOT/"data/mock/core/sources.json"
PROJECTS=ROOT/"data/mock/market/projects.json"
DST=ROOT/"data/processed/market/commercial-offer-review.json"
SOURCE_HOST="batdongsanhpr.com"

def read(p):return json.loads(p.read_text(encoding="utf8"))
def validate(data,source_ids,project_ids,today):
    if data.get("schema_version")!=1 or data.get("record_count")!=len(data.get("price_leads",[])):
        raise ValueError("Malformed commercial price leads")
    if data["review_date"]>today.isoformat():raise ValueError("Future-dated review")
    prices=[]
    for p in data["price_leads"]:
        if p["source_id"]!="hpr-izumi-broker" or p["source_id"] not in source_ids or p["project_id"] not in project_ids:
            raise ValueError("Unknown source or project")
        u=urlsplit(p["source_url"])
        if u.scheme!="https" or u.hostname not in (SOURCE_HOST,"www."+SOURCE_HOST):
            raise ValueError("Source must remain exact HPR dealer domain")
        if type(p.get("starting_asking_price_vnd")) not in (int,float) or p["starting_asking_price_vnd"]<=0:
            raise ValueError("Price must be positive source-stated VND")
        if p.get("price_type")!="dealer-reported-starting-list-price" or p.get("signed_original_price_sheet_verified") is not False:
            raise ValueError("Unverified minimum must not look like an official unit quote")
        if any(p.get(k) is not False for k in ("eligible_for_fs_asp","eligible_for_net_price","eligible_for_pv",
                                             "valid_contract_selling_price_verified")):
            raise ValueError("Broker starting price may not be promoted to financial model")
        if p.get("individual_unit_code") is not None or p.get("land_area_sqm") is not None or p.get("construction_floor_area_sqm") is not None:
            raise ValueError("Do not pair an unknown unit's minimum price with another unit's area")
        if p.get("source_report_date")>today.isoformat() or p.get("review_date")>today.isoformat():
            raise ValueError("Source reports cannot be future dated")
        prices.append({"id":p["id"],"project_id":p["project_id"],"subproject":p["subproject"],"zone":p.get("zone"),
            "product_type":p["product_type"],"starting_price_vnd":p["starting_asking_price_vnd"],
            "comparison_level":"dealer-report-per-product-zone-minimum",
            "source_id":p["source_id"],"source_url":p["source_url"],"source_report_date":p["source_report_date"],
            "last_human_review_date":p["review_date"],
            "contract_net_price_vnd":None,"project_asp_vnd_per_sqm":None,"discount_pct_applied":None,
            "payment_pv_vnd":None,"price_status":"unverified-dealer-lead",
            "primary_price_sheet_received":False,"fs_eligible":False})
    versions=[]
    for e in data["policy_events"]:
        if e.get("source_id")!="hpr-izumi-broker" or e.get("signed_notice_verified") is not False or e.get("discounts_verified") is not False:
            raise ValueError("Policy notice original and discounts unverified")
        if e.get("review_date")>today.isoformat():raise ValueError("Future policy review")
        if urlsplit(e["source_url"]).hostname not in (SOURCE_HOST,"www."+SOURCE_HOST):raise ValueError("Invalid policy source")
        versions.append({"id":e["id"],"project_id":e["project_id"],"subproject":e["subproject"],
            "reported_notice_id":e["reported_notice_id"],"notice_date":e["notice_date"],
            "reported_valid_from":e.get("reported_valid_from"),"reported_valid_until":e.get("reported_valid_until"),
            "status":e["status"],"successor_notice_id":e.get("successor_notice_id"),
            "signed_notice_received":False,"discounts_verified":False,
            "source_id":e["source_id"],"source_url":e["source_url"],"review_date":e["review_date"]})
    tb143=next((r for r in versions if r["reported_notice_id"].startswith("TB143/")),None)
    tb153=next((r for r in versions if r["reported_notice_id"].startswith("TB153/")),None)
    if not (tb143 and tb153 and tb143["successor_notice_id"]==tb153["reported_notice_id"] and
            tb143["reported_valid_until"]<tb153["reported_valid_from"]):
        raise ValueError("Missing coherent policy replacement relation")
    ids=[x["id"] for x in prices+versions]
    if len(ids)!=len(set(ids)):raise ValueError("Duplicate lead identifiers")
    return prices,versions

def build(data,source_registry,projects,as_of):
    prices,versions=validate(data,{x["id"] for x in source_registry["data"]},
                              {x["id"] for x in projects["data"]},as_of)
    digest=hashlib.sha256(json.dumps([prices,versions],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    return {"schema_version":1,"build_revision":digest,"review_as_of":data["review_date"],
        "data_mode":"third-party-dealer-leads-require-primary-documents",
        "source_price_leads":len(prices),"policy_changes_reported":len(versions),
        "verified_developer_price_rows":0,"eligible_price_benchmarks":0,
        "verified_current_payment_policies":0,"eligible_net_price_pv":0,
        "missing_originals":list(data.get("unverified_fields",[])),
        "prices":prices,"policy_versions":versions,
        "no_automatic_promotion":True,
        "disclaimer":"Broker quotes are reported starting minima, not the price of a specific unit, developer ASP, verified discounts or contract PV. TB153 replaces TB143 per dealer report; obtain signed originals before use in FS."}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",default=str(DST));args=p.parse_args()
    result=build(read(SRC),read(SOURCES),read(PROJECTS),date.today())
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    txt=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if dest.exists() and dest.read_text(encoding="utf8")==txt:
        print("No change in verified input evidence; kept review queue unchanged.")
        return
    dest.write_text(txt,encoding="utf8")
    print(f"Broker price leads {result['source_price_leads']}; contract net/PV eligible=0; requires signed TB153.")

if __name__=="__main__":main()
