"""Validate scope-restricted listing prices without promoting them to project ASP."""
from __future__ import annotations
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"data/mock/market/listing-scope-evidence.json"
LISTING=ROOT/"data/mock/market/listing-observations.json"
PROJECTS=ROOT/"data/mock/market/projects.json"
EXPECTED={
    "the-9-stellars":("https://batdongsan.com.vn/ban-can-ho-chung-cu-the-9-stellars","apartment-only"),
    "celesta-gold":("https://batdongsan.com.vn/ban-can-ho-chung-cu-celesta-gold","publisher-faq-indicative"),
}
NUM=r"(\d+(?:[.,]\d+)?)"
RANGE_PATTERNS=(
    re.compile(NUM+r"\s*[-–]\s*"+NUM+r"\s*tr\s*/\s*m[²2]",re.I),
    re.compile(NUM+r"\s*triệu\s*/\s*m[²2]\s*[-–]\s*"+NUM+r"\s*triệu\s*/\s*m[²2]",re.I),
)
DATE_PATTERN=re.compile(r"Cập nhật tin đăng gần đây nhất\s*\|?\s*(\d{2})-(\d{2})-(20\d\d)",re.I)

def decimal(s):
    return float(str(s).replace(",","."))

def evidence_price(text):
    for pattern in RANGE_PATTERNS:
        m=pattern.search(text or "")
        if m:
            return tuple(int(round(decimal(v)*1000000)) for v in m.groups())
    return None

def evidence_last_listing(text):
    m=DATE_PATTERN.search(text or "")
    if not m:
        return None
    try:
        return date(int(m.group(3)),int(m.group(2)),int(m.group(1))).isoformat()
    except ValueError:
        return None

def evidence_trend(text):
    m=re.search(NUM+r"\s*%\s*Giá bán đã\s*(giảm|tăng)",text or "",re.I)
    if not m:
        return None
    val=decimal(m.group(1))/100
    return round(-val if m.group(2).lower()=="giảm" else val,6)

def check(rows, observations, project_ids, today):
    errors=[]
    ids=set()
    latest={}
    for x in sorted(observations,key=lambda r:(r.get("project_id") or "",r.get("observation_date") or "")):
        latest[x.get("project_id")]=x
    for x in rows:
        pid=x.get("project_id")
        uri=x.get("source_url")
        expected=EXPECTED.get(pid)
        if x.get("id") in ids:
            errors.append(f"{pid}: duplicated evidence ID")
        ids.add(x.get("id"))
        if pid not in project_ids or expected is None or (uri,x.get("price_scope"))!=expected:
            errors.append(f"{pid}: unexpected project/scope or source link")
            continue
        if urlsplit(uri).scheme!="https" or urlsplit(uri).hostname!="batdongsan.com.vn":
            errors.append(f"{pid}: source must use official HTTPS domain")
        if x.get("coverage_status") not in ("segment-only-not-project-aggregate","reference-only-not-chartable"):
            errors.append(f"{pid}: invalid scope-only coverage")
        if x.get("source_id")!="batdongsan-com-vn":
            errors.append(f"{pid}: unknown source")
        try:
            reviewed=date.fromisoformat(x["review_date"])
            last=date.fromisoformat(x["latest_listing_date"])
            if reviewed>today or last>reviewed or (reviewed-last).days>35:
                errors.append(f"{pid}: future or stale source dates")
        except (KeyError,ValueError):
            errors.append(f"{pid}: invalid source dates")
        evidence=x.get("evidence") or {}
        if evidence_price(evidence.get("price"))!=(
            x.get("asking_price_low_vnd_per_m2"),
            x.get("asking_price_high_vnd_per_m2"),
        ):
            errors.append(f"{pid}: cited text does not contain reference price")
        if evidence_last_listing(evidence.get("last_listing"))!=x.get("latest_listing_date"):
            errors.append(f"{pid}: last-listing date not evidenced")
        if evidence_trend(evidence.get("trend"))!=x.get("asking_price_change_1y_pct"):
            errors.append(f"{pid}: quoted segment 1Y trend mismatch")
        if pid=="the-9-stellars" and x.get("asset_type")!="apartment":
            errors.append(f"{pid}: reference must be apartment-only")
        if x.get("asking_price_low_vnd_per_m2",0)<=0 or x.get("asking_price_high_vnd_per_m2",0)<=x.get("asking_price_low_vnd_per_m2",0):
            errors.append(f"{pid}: invalid positive price")
        previous=latest.get(pid) or {}
        if previous.get("asking_price_low_vnd_per_m2") is not None:
            errors.append(f"{pid}: scoped evidence intended only for unpriced project-level datasets")
        if previous.get("coverage_status")!="partial":
            errors.append(f"{pid}: source scope mixed into full project history")
    return errors

def main():
    payload=json.loads(FILE.read_text(encoding="utf-8"))
    original=json.loads(LISTING.read_text(encoding="utf-8"))["data"]
    projects={x["id"] for x in json.loads(PROJECTS.read_text(encoding="utf-8"))["data"]}
    problems=check(payload["data"],original,projects,date.today())
    if payload.get("record_count")!=len(payload["data"]):
        problems.append("record_count mismatch")
    if problems:
        raise SystemExit("\n".join(problems))
    print("Scope evidence PASS: 2 separately sourced, neither promoted to comparable project ASP.")

if __name__=="__main__":
    main()
