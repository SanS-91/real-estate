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
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/mock/market/individual-product-evidence.json"
PROJECTS=ROOT/"data/mock/market/projects.json"
SOURCES=ROOT/"data/mock/core/sources.json"
OUT=ROOT/"data/processed/market/product-comparables.json"
MUABAN=ROOT/"data/mock/market/verified-muaban-unit-listings.json"
REVER=ROOT/"data/mock/market/verified-unit-listings.json"
MUABAN_HEALTH=ROOT/"data/state/market-muaban-source-health.json"
REVER_HEALTH=ROOT/"data/state/market-rever-source-health.json"
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

def recently_checked(report, now):
    try:
        checked=datetime.fromisoformat(report["generated_at"].replace("Z","+00:00"))
        return checked.tzinfo is not None and timedelta(0)<=(now-checked)<=timedelta(hours=48)
    except (ValueError, KeyError, TypeError):
        return False

def verified_unit_auto_rows(projects, sources, now, muaban, rever, muaban_health, rever_health):
    """Apply the existing independent-source and two-run contract; fail closed."""
    idmap={x["id"]:x for x in projects["data"]}
    registry={x["id"] for x in sources["data"]}
    days=now.date()
    valid=[]
    for provider,offers,health in (("muaban-vn",muaban,muaban_health),("rever-vn",rever,rever_health)):
        if not recently_checked(health,now):
            continue
        for r in offers.get("data",[]):
            pid=r.get("project_id")
            if pid not in idmap or provider not in registry or r.get("source_id")!=provider:
                continue
            if r.get("review_status")!="automated-two-hosted-checks" or r.get("asset_type")!="apartment":
                continue
            if r.get("metric_type")!="single-listing-asking-price-per-sqm" or r.get("market_layer")!="individual-listing-asking":
                continue
            if len({str(x) for x in r.get("verification_run_ids",[])})<2:
                continue
            amount=r.get("listing_price_vnd")
            area=r.get("listed_area_sqm")
            if not positive_number(amount) or not positive_number(area) or not positive_number(r.get("value_vnd_per_m2")):
                continue
            if abs(amount/area-r["value_vnd_per_m2"])/(amount/area)>0.015:
                continue
            uri=urlsplit(r.get("source_url",""))
            expected="muaban.net" if provider=="muaban-vn" else "rever.vn"
            if uri.scheme!="https" or uri.hostname not in (expected,"www."+expected):
                continue
            if provider=="muaban-vn":
                try:
                    listed=date.fromisoformat(r["source_listed_date"])
                    expiry=date.fromisoformat(r["source_expiration_date"])
                except (ValueError,KeyError,TypeError):
                    continue
                if not listed<=days<=expiry or (days-listed).days>90:
                    continue
                scan=next((x for x in health.get("sources",[]) if x.get("project_id")==pid),None)
                if not scan or scan.get("access")!="reachable" or scan.get("qualified",0)<1:
                    continue
            else:
                try:
                    listed=date.fromisoformat(r["source_updated_date"])
                except (ValueError,KeyError,TypeError):
                    continue
                if not 0<=(days-listed).days<=90:continue
                scan=next((x for x in health.get("projects",[]) if x.get("project_id")==pid),None)
                if not scan or not any(c.get("access_status")=="reachable" for c in scan.get("catalogs",[])):
                    continue
                if scan.get("recent_90_days",0)<1:continue
            valid.append({
              "id":r.get("id") or provider+"-"+str(r["listing_id"]),
              "project_id":pid, "project_name":idmap[pid]["name"],
              "region_id":idmap[pid]["region_ids"][0],
              "phase_name":None, "product_type":"apartment",
              "market_layer":"two-run-source-verified-unit-asking",
              "listing_status":"verified-by-two-runs-and-current-source-check",
              "price_vnd_per_unit":amount,"land_area_sqm":None,
              "advertised_apartment_area_sqm":area,"construction_floor_area_sqm":None,
              "unit_price_vnd_per_sqm":r["value_vnd_per_m2"],
              "price_area_basis":"publisher-stated-apartment-area-not-verified-net",
              "price_unit_label_vi":"triệu đồng/m² diện tích căn hộ theo tin đăng",
              "payment_scheme_status":"not-officially-verified",
              "verified_payment_milestones":[],"upfront_claim_vnd":None,
              "payment_claim_note":None,"handover_verified_date":None,
              "handover_claim_date":None,"discount_to_pv_vnd":None,
              "is_verified_live_offer":True,"fs_asp_eligible":False,
              "fs_absorption_eligible":False,
              "source_id":provider,"source_url":r["source_url"],
              "source_listing_id":str(r["listing_id"]),
              "source_listed_date":listed.isoformat(),
              "source_review_date":r.get("review_date") or listed.isoformat(),
              "methodology_note":"Two independent publisher checks and a recent source-health report; individual asking advertisement only, not project price, transaction or guaranteed current stock."
            })
    unique={}
    for row in valid:
        unique[(row["source_id"],row["source_listing_id"])]=row
    return list(unique.values())

def build(raw, projects, sources, as_of, live_rows=None):
    if raw["record_count"]!=len(raw["records"]):raise ValueError("Raw records count mismatch")
    ids={x["id"]:x for x in projects["data"]}
    source_ids={x["id"] for x in sources["data"]}
    seen=set()
    rows=[]
    for rawrow in raw["records"]:
        if rawrow["id"] in seen:raise ValueError("Duplicate listing ID")
        seen.add(rawrow["id"])
        rows.append(checked_row(rawrow,ids,source_ids,as_of))
    rows.extend(live_rows or [])
    rows.sort(key=lambda x:(not x["is_verified_live_offer"],x["project_id"],-date.fromisoformat(x["source_listed_date"]).toordinal(),x["id"]))
    cov=[]
    for pid in WATCHLIST:
        if pid not in ids:raise ValueError(f"Missing watched project {pid}")
        subset=[r for r in rows if r["project_id"]==pid]
        cov.append({"project_id":pid,"project_name":ids[pid]["name"],
                    "region_id":ids[pid]["region_ids"][0],
                    "historical_individual_offers":sum(not r["is_verified_live_offer"] for r in subset),
                    "live_offers_verified":sum(r["is_verified_live_offer"] for r in subset),"official_payment_schedules_verified":0,
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
      "record_count":len(rows),"historical_seller_asking_count":sum(not x["is_verified_live_offer"] for x in rows),
      "verified_live_count":sum(x["is_verified_live_offer"] for x in rows),"official_payment_schedules":0,
      "region_count":len({x["region_id"] for x in rows}),
      "watchlist_coverage":cov,"data":rows
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default=str(OUT))
    args=parser.parse_args()
    now=datetime.now(timezone.utc)
    projects=read(PROJECTS)
    sources=read(SOURCES)
    live=verified_unit_auto_rows(projects,sources,now,
      read(MUABAN),read(REVER),read(MUABAN_HEALTH),read(REVER_HEALTH))
    payload=build(read(RAW),projects,sources,now.date(),live)
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    output=json.dumps(payload,ensure_ascii=False,indent=2)+"\n"
    if path.exists() and path.read_text(encoding="utf-8")==output:
        print("No source changes. Historical product benchmark unchanged.")
        return
    path.write_text(output,encoding="utf-8")
    print(f"Built {payload['historical_seller_asking_count']} historical product offers; two-run fresh offers={payload['verified_live_count']}.")

if __name__=="__main__":main()
