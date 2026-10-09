"""Guard reviewed OneHousing nested-apartment price references; no parent ASP dilution."""
from __future__ import annotations
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"data/mock/market/alternative-subproject-monthly-evidence.json"
PARENT=ROOT/"data/mock/market/projects.json"
SOURCE=ROOT/"data/mock/core/sources.json"
PORTAL=ROOT/"data/mock/market/listing-observations.json"
EXISTING=ROOT/"data/mock/market/alternative-price-evidence.json"
LOCKED={
  "onehousing-lumiere-boulevard-apartment-2026-09":(
    "Lumière Boulevard","lumiere-boulevard",
    "https://onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Lumiere-Boulevard.34",
    "2026-09",73_400_000,57_440_000,100_060_000),
  "onehousing-masteri-centre-point-apartment-2026-09":(
    "Masteri Centre Point","masteri-centre-point",
    "https://beta.onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Masteri-Centre-Point.53",
    "2026-09",70_900_000,53_060_000,224_870_000),
}
PRICE=re.compile(r"(\d+(?:[.,]\d+)?)\s*triệu\s*/?\s*m[²2]",re.I)
RANGE=re.compile(r"Khoảng giá:\s*(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*triệu",re.I)
MONTH=re.compile(r"tháng\s*(\d{1,2})/(20\d{2})",re.I)

def millions(v):
    return round(float(v.replace(",","."))*1_000_000)

def validate(rows, project_ids, sources, today):
    errors=[];seen=set()
    for row in rows:
        rid=row.get("id");spec=LOCKED.get(rid)
        if rid in seen:errors.append(f"{rid}: duplicate ID")
        seen.add(rid)
        if spec is None:
            errors.append(f"{rid}: unexpected subproject source")
            continue
        name,slug,url,period,val,low,high=spec
        for k,expected in (
            ("project_id","vinhomes-grand-park"),("subproject_name",name),("subproject_id",slug),
            ("source_url",url),("source_id","onehousing-vn"),("asset_type","apartment"),
            ("metric_type","popular-asking-price-per-sqm"),("period_type","month"),
            ("period",period),("value_vnd_per_m2",val),("range_low_vnd_per_m2",low),
            ("range_high_vnd_per_m2",high),("source_capture_kind","reviewed-source-indexed-period"),
            ("source_publication_date",None)):
            if row.get(k)!=expected:errors.append(f"{rid}: scope/value mismatch {k}")
        if row.get("project_id") not in project_ids or row.get("source_id") not in sources:
            errors.append(f"{rid}: source/project not registered")
        parsed=urlsplit(row.get("source_url",""))
        if parsed.scheme!="https" or parsed.hostname not in ("onehousing.vn","beta.onehousing.vn") or parsed.query or parsed.fragment:
            errors.append(f"{rid}: unsafe publisher URL")
        try:
            review=date.fromisoformat(row["review_date"])
            if review>today or row["period"]>review.strftime("%Y-%m"):
                errors.append(f"{rid}: future month/review")
        except (KeyError,ValueError):
            errors.append(f"{rid}: invalid review date")
        e=row.get("evidence",{})
        quoted_month=MONTH.search(e.get("period",""))
        if not quoted_month or f"{quoted_month.group(2)}-{int(quoted_month.group(1)):02d}"!=period or name not in e.get("period",""):
            errors.append(f"{rid}: source month/project evidence missing")
        quoted_price=PRICE.search(e.get("metric",""))
        quoted_range=RANGE.search(e.get("range",""))
        if not quoted_price or millions(quoted_price.group(1))!=val:
            errors.append(f"{rid}: modal price doesn't match quote")
        if not quoted_range or (millions(quoted_range.group(1)),millions(quoted_range.group(2)))!=(low,high):
            errors.append(f"{rid}: asking range doesn't match quote")
        if not (0<low<=val<=high):
            errors.append(f"{rid}: incoherent modal/range")
        if "not" not in row.get("methodology_note","").lower():
            errors.append(f"{rid}: methodology caveat missing")
        if row.get("average_asp") is not None or row.get("asking_price_change_1y_pct") is not None or row.get("trend_ready") is True:
            errors.append(f"{rid}: project ASP/trend fields forbidden")
    if seen!=set(LOCKED):
        errors.append("expected exactly two independent subproject records")
    return errors

def main():
    d=json.loads(EVIDENCE.read_text(encoding="utf-8"))
    projects={p["id"] for p in json.loads(PARENT.read_text(encoding="utf-8"))["data"]}
    sources={s["id"] for s in json.loads(SOURCE.read_text(encoding="utf-8"))["data"]}
    errors=validate(d["data"],projects,sources,date.today())
    portal=json.loads(PORTAL.read_text(encoding="utf-8"))
    existing=json.loads(EXISTING.read_text(encoding="utf-8"))
    if d.get("record_count")!=len(d.get("data",[])) or d.get("record_count")!=2:
        errors.append("subproject baseline count mismatch")
    if portal["record_count"]!=18 or existing["record_count"]!=4:
        errors.append("original market price records changed")
    if errors:raise SystemExit("\n".join(errors))
    print("PASS: two distinct OneHousing nested apartment references; 12 parent projects and portal asking history unchanged.")

if __name__=="__main__":main()
