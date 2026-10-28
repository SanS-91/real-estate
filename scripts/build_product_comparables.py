#!/usr/bin/env python3
"""Transform real dated single-unit advertisements into strict FS-comparable rows.

Never infer missing area, current availability, transactions, developer
policies, phased payment milestones or discounted prices from broker prose.
Output is deterministic: a new build run is not a new market observation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from datetime import date
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/mock/market/individual-product-evidence.json"
PROJECTS=ROOT/"data/mock/market/projects.json"
SOURCES=ROOT/"data/mock/core/sources.json"
OUT=ROOT/"data/processed/market/product-comparables.json"
LAND_TYPES={"landlot","townhouse","corner-townhouse","semidetached-villa","detached-villa"}
FLAT_TYPES={"apartment"}
ALLOWED_STATUS={"expired-at-review","unverified-current"}
WATCHLIST=["izumi-city","aqua-city","springville","elyse-island","kita-airport-city","nam-long-ii-central-lake"]

def read(path):return json.loads(path.read_text(encoding="utf-8"))
def positive_number(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and x>0

def checked_row(r, project_ids, source_ids, as_of):
    if r["project_id"] not in project_ids or r["source_id"] not in source_ids:
        raise ValueError(f"Unknown project or source: {r.get('id')}")
    if r["source_id"]!="cafeland-listings" or urlsplit(r["source_url"]).hostname!="nhadat.cafeland.vn":
        raise ValueError(f"Unapproved provenance: {r.get('id')}")
    if urlsplit(r["source_url"]).scheme!="https":
        raise ValueError("Source must be HTTPS")
    t=r["product_type"]
    if t not in LAND_TYPES|FLAT_TYPES:raise ValueError(f"Unsupported product: {t}")
    if r["listing_status"] not in ALLOWED_STATUS:
        raise ValueError(f"Unclear source expiry: {r['id']}")
    if r["price_basis"]!="seller-asking-single-listing":raise ValueError("Not a single listing")
    date_listed=date.fromisoformat(r["listed_date"])
    date_reviewed=date.fromisoformat(r["reviewed_date"])
    if date_listed>date_reviewed or date_reviewed>as_of:
        raise ValueError(f"Invalid listing chronology: {r['id']}")
    if not positive_number(r["total_asking_vnd"]) or not positive_number(r["listed_unit_area_sqm"]) or not positive_number(r["publisher_unit_rate_vnd_per_sqm"]):
        raise ValueError("Missing numeric price or area")
    if r.get("floor_area_sqm") is not None:
        raise ValueError("Construction floor area not independently established")
    if t in LAND_TYPES:
        if r.get("area_basis")!="land-area-reported-by-publisher" or r.get("land_area_sqm")!=r["listed_unit_area_sqm"]:
            raise ValueError("Landed denominator must be explicitly source-reported land area")
        basis="triệu đồng/m² đất (theo tin đăng)"
    else:
        if r.get("land_area_sqm") is not None or r.get("area_basis")!="publisher-stated-apartment-area-not-verified-net":
            raise ValueError("Apartment area must not be treated as land, NFA or certified floor area")
        basis="triệu đồng/m² diện tích căn hộ theo tin đăng"
    implied=r["total_asking_vnd"]/r["listed_unit_area_sqm"]
    if abs(implied-r["publisher_unit_rate_vnd_per_sqm"])/implied>0.012:
        raise ValueError(f"Publisher unit quote and total price inconsistent: {r['id']}")
    up=r.get("payment_upfront_claim_vnd")
    if up is not None and (not positive_number(up) or up>=r["total_asking_vnd"] or not r.get("payment_claim_note")):
        raise ValueError("Invalid broker payment claim")
    if r.get("payment_schedule") or r.get("verified_developer_payment") or r.get("sales_units") is not None:
        raise ValueError("Never promote a broker payment claim or sales velocity")
    return {
        "id":r["id"],"project_id":r["project_id"],"project_name":project_ids[r["project_id"]]["name"],
        "region_id":project_ids[r["project_id"]]["region_ids"][0],
        "phase_name":r.get("phase_name"),"product_type":t,
        "market_layer":"historical-individual-asking-only",
        "listing_status":r["listing_status"],
        "price_vnd_per_unit":r["total_asking_vnd"],"land_area_sqm":r.get("land_area_sqm"),
        "advertised_apartment_area_sqm":r["listed_unit_area_sqm"] if t in FLAT_TYPES else None,
        "construction_floor_area_sqm":None,
        "unit_price_vnd_per_sqm":r["publisher_unit_rate_vnd_per_sqm"],
        "price_area_basis":r["area_basis"],"price_unit_label_vi":basis,
        "payment_scheme_status":"not-officially-verified",
        "verified_payment_milestones":[],
        "upfront_claim_vnd":up,"payment_claim_note":r.get("payment_claim_note"),
        "handover_verified_date":None,
        "handover_claim_date":r.get("hand_over_claim_date"),
        "discount_to_pv_vnd":None,
        "is_verified_live_offer":False,"fs_asp_eligible":False,"fs_absorption_eligible":False,
        "source_id":r["source_id"],"source_url":r["source_url"],
        "source_listing_id":r["source_listing_id"],"source_listed_date":r["listed_date"],
        "source_review_date":r["reviewed_date"],"methodology_note":r["methodology_note"]
    }

def build(raw, projects, sources, as_of):
    if raw["record_count"]!=len(raw["records"]):raise ValueError("Raw records count mismatch")
    ids={x["id"]:x for x in projects["data"]}
    source_ids={x["id"] for x in sources["data"]}
    seen=set()
    rows=[]
    for rawrow in raw["records"]:
        if rawrow["id"] in seen:raise ValueError("Duplicate listing ID")
        seen.add(rawrow["id"])
        rows.append(checked_row(rawrow,ids,source_ids,as_of))
    rows.sort(key=lambda x:(x["project_id"],-date.fromisoformat(x["source_listed_date"]).toordinal(),x["id"]))
    cov=[]
    for pid in WATCHLIST:
        if pid not in ids:raise ValueError(f"Missing watched project {pid}")
        subset=[r for r in rows if r["project_id"]==pid]
        cov.append({"project_id":pid,"project_name":ids[pid]["name"],
                    "region_id":ids[pid]["region_ids"][0],
                    "historical_individual_offers":len(subset),
                    "live_offers_verified":0,"official_payment_schedules_verified":0,
                    "project_asp_available_from_this_dataset":False,
                    "unverified_fields":["current_listing_status","developer_net_selling_price",
                                         "land_area" if not subset else "construction_floor_area",
                                         "discount_or_financing_policy","contractual_handover"]})
    revision=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    return {
      "schema_version":1,"build_revision":revision,
      "evidence_as_of":max((x["source_review_date"] for x in rows),default=None),
      "generated_from":"data/mock/market/individual-product-evidence.json",
      "refresh_policy":"rebuild-on-source-change; no synthetic dates, no automatic seller price promotion",
      "record_count":len(rows),"historical_seller_asking_count":len(rows),
      "verified_live_count":0,"official_payment_schedules":0,
      "region_count":len({x["region_id"] for x in rows}),
      "watchlist_coverage":cov,"data":rows
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default=str(OUT))
    args=parser.parse_args()
    payload=build(read(RAW),read(PROJECTS),read(SOURCES),date.today())
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    output=json.dumps(payload,ensure_ascii=False,indent=2)+"\n"
    if path.exists() and path.read_text(encoding="utf-8")==output:
        print("No source changes. Historical product benchmark unchanged.")
        return
    path.write_text(output,encoding="utf-8")
    print(f"Built {payload['record_count']} historical product offers and {len(payload['watchlist_coverage'])} watchlist checks; verified live=0.")

if __name__=="__main__":main()
