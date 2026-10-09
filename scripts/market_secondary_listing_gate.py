"""Verify three sourced single-unit price references, never infer project-wide ASP."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/mock/market/secondary-listing-evidence.json"
SOURCE = ROOT / "data/mock/core/sources.json"
PROJECT = ROOT / "data/mock/market/projects.json"
PORTAL = ROOT / "data/mock/market/listing-observations.json"
SCOPED = ROOT / "data/mock/market/listing-scope-evidence.json"
EXPECTED = {
    "cafeland-izumi-city-garden-townhouse-2026-05-26": {
        "project_id":"izumi-city","asset_type":"townhouse","date":"2026-05-26",
        "listing_id":"26042484684",
        "url":"https://nhadat.cafeland.vn/can-nha-pho-view-pho-va-view-cong-vien-thoang-2-mat-gia-chi-68trm2-2484684.html",
        "value":68_500_000,"area":164,"total":11_243_000_000},
    "cafeland-essensia-parkway-semidetached-villa-2026-10-08": {
        "project_id":"essensia-parkway","asset_type":"semidetached-villa","date":"2026-10-08",
        "listing_id":"26103191696",
        "url":"https://nhadat.cafeland.vn/biet-thu-truc-duong-nguyen-huu-tho-so-huu-lau-dai-gia-325-ty-3191696.html",
        "value":203_000_000,"area":160,"total":32_500_000_000},
    "cafeland-the-9-stellars-alta-heights-apartment-2025-01-05": {
        "project_id":"the-9-stellars","asset_type":"apartment","date":"2025-01-05",
        "listing_id":"25012259497",
        "url":"https://nhadat.cafeland.vn/giai-doan-1-can-ho-alta-height-thuoc-du-an-the-9-stellars-ngay-ga-metro-2259497.html",
        "value":62_000_000,"area":100,"total":6_200_000_000},
}
PRICE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*triệu\s*/\s*m[²2]",re.I)
AMOUNTS = {
    "cafeland-izumi-city-garden-townhouse-2026-05-26": "11 tỷ 243 triệu",
    "cafeland-essensia-parkway-semidetached-villa-2026-10-08": "32 tỷ 500 triệu",
    "cafeland-the-9-stellars-alta-heights-apartment-2025-01-05": "6 tỷ 200 triệu",
}

def validate(rows, project_ids, source_ids, today):
    errors, seen = [], set()
    for row in rows:
        rid=row.get("id")
        expected=EXPECTED.get(rid)
        if rid in seen:
            errors.append(f"{rid}: duplicate evidence ID")
        seen.add(rid)
        if expected is None:
            errors.append(f"{rid}: unexpected evidence")
            continue
        for field,key in (
            ("project_id","project_id"),("asset_type","asset_type"),("source_url","url"),
            ("period","date"),("source_publication_date","date"),("listing_id","listing_id"),
            ("value_vnd_per_m2","value"),("listed_area_sqm","area"),("listed_total_vnd","total")):
            if row.get(field)!=expected[key]:
                errors.append(f"{rid}: source mapping changed: {field}")
        if row.get("project_id") not in project_ids or row.get("source_id") not in source_ids:
            errors.append(f"{rid}: unregistered project or source")
        if row.get("source_id")!="cafeland-listings":
            errors.append(f"{rid}: unsupported publisher")
        uri=urlsplit(row.get("source_url",""))
        if (uri.scheme,uri.hostname,uri.query,uri.fragment)!=("https","nhadat.cafeland.vn","",""):
            errors.append(f"{rid}: invalid publisher URL")
        if row.get("period_type")!="date" or row.get("metric_type")!="single-listing-asking-price-per-sqm":
            errors.append(f"{rid}: project aggregate/period confusion")
        try:
            src=date.fromisoformat(row["source_publication_date"])
            checked=date.fromisoformat(row["review_date"])
            if src>checked or checked>today:
                errors.append(f"{rid}: future source/review date")
        except (ValueError,KeyError):
            errors.append(f"{rid}: invalid date")
        ev=row.get("evidence",{})
        if expected["date"].split("-")[2]+"-"+expected["date"].split("-")[1]+"-"+expected["date"].split("-")[0] not in ev.get("date",""):
            errors.append(f"{rid}: source quote missing date")
        if expected["listing_id"] not in ev.get("listing",""):
            errors.append(f"{rid}: source quote missing listing ID")
        if expected["project_id"] == "the-9-stellars":
            has_project = "The 9 Stellars" in ev.get("project","")
        else:
            has_project = expected["project_id"].replace("-"," ").lower() in ev.get("project","").lower()
        if not has_project:
            errors.append(f"{rid}: source quote missing matching project")
        m=PRICE_RE.search(ev.get("price",""))
        if not m or round(float(m.group(1).replace(",","."))*1_000_000)!=row.get("value_vnd_per_m2"):
            errors.append(f"{rid}: price quote mismatch")
        if not re.search(r"\b"+str(expected["area"])+r"\s*m[²2]\b",ev.get("area",""),re.I):
            errors.append(f"{rid}: area quote mismatch")
        if ev.get("total")!=AMOUNTS[rid]:
            errors.append(f"{rid}: advertised total quote mismatch")
        # Single-listing headline numbers may be rounded and differ by < 1%.
        if not (isinstance(row.get("listed_total_vnd"),int) and isinstance(row.get("listed_area_sqm"),int) and
                abs(row["listed_total_vnd"] - row["value_vnd_per_m2"]*row["listed_area_sqm"]) / row["listed_total_vnd"] <= .01):
            errors.append(f"{rid}: price / area / total contradictory")
        if row.get("publisher_claim_status") not in (
                "source-reported-asking-not-transaction","expired-source-reported-asking-not-transaction"):
            errors.append(f"{rid}: invalid confidence/claim status")
        if "not" not in row.get("methodology_note","").lower():
            errors.append(f"{rid}: price/coverage caveat missing")
        if row.get("source_data_as_of") or row.get("average_asp") or row.get("asking_price_change_1y_pct"):
            errors.append(f"{rid}: must not derive project price/portal trend")
    if set(EXPECTED) != seen:
        errors.append("expected three independent single-listing references")
    return errors

def main():
    data=json.loads(DATA.read_text(encoding="utf-8"))
    projects={x["id"] for x in json.loads(PROJECT.read_text(encoding="utf-8"))["data"]}
    sources={x["id"] for x in json.loads(SOURCE.read_text(encoding="utf-8"))["data"]}
    errors=validate(data["data"],projects,sources,date.today())
    portal=json.loads(PORTAL.read_text(encoding="utf-8"))
    scope=json.loads(SCOPED.read_text(encoding="utf-8"))
    if data.get("record_count")!=3 or data["record_count"]!=len(data["data"]):
        errors.append("unexpected record count")
    if portal["record_count"]!=18 or scope["record_count"]!=4:
        errors.append("existing portal/history contracts must remain unchanged")
    if errors:
        raise SystemExit("\n".join(errors))
    print("PASS: 3 independent dated single-unit prices for Izumi, Essensia and The 9 Stellars; portal history untouched.")

if __name__=="__main__":
    main()
