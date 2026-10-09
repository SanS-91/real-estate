"""Guard independently reviewed non-comparable alternative Market price evidence."""
from __future__ import annotations
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/mock/market/alternative-price-evidence.json"
PROJECTS = ROOT / "data/mock/market/projects.json"
SOURCES = ROOT / "data/mock/core/sources.json"
LOCKED_LINKS = {
    "onehousing-vinhomes-grand-park-apartment-2026-10": (
        "vinhomes-grand-park", "onehousing-vn",
        "https://onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Vinhomes-Grand-Park.1012",
        "popular-asking-price-per-sqm", "2026-10"),
    "rever-vinhomes-grand-park-apartment-listing-2026-09-16": (
        "vinhomes-grand-park", "rever-vn",
        "https://rever.vn/mua/can-ho-vinhomes-grand-park-23",
        "single-listing-asking-price-per-sqm", "2026-09-16"),
    "rever-the-privia-launch-floor-2023-11-14": (
        "the-privia", "rever-vn",
        "https://blog.rever.vn/the-privia-khang-dien-du-dieu-kien-mua-ban-rever-chinh-thuc-phan-phoi",
        "historical-launch-starting-price-per-sqm", "2023-11-14"),
    "onehousing-the-global-city-grand-view-launch-floor-2024-11-12": (
        "the-global-city", "onehousing-vn",
        "https://onehousing.vn/blog/can-ho-the-global-city",
        "historical-launch-starting-price-per-sqm", "2024-11-12"),
}
PRICE = re.compile(r"(\d+(?:[.,]\d+)?)\s*triệu\s*/\s*m(?:²|2)", re.I)
RANGE = re.compile(r"Khoảng giá\s*:\s*(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*triệu", re.I)

def millions(raw):
    return int(round(float(raw.replace(",", ".")) * 1_000_000))

def validate(rows, source_ids, project_ids, today):
    problems = []
    seen = set()
    for row in rows:
        rid = row.get("id", "")
        locked = LOCKED_LINKS.get(rid)
        if rid in seen:
            problems.append(f"{rid}: duplicated ID")
        seen.add(rid)
        if locked is None or (row.get("project_id"), row.get("source_id"),
               row.get("source_url"), row.get("metric_type"), row.get("period")) != locked:
            problems.append(f"{rid}: unapproved publisher/project/metric mapping")
            continue
        if row["source_id"] not in source_ids or row["project_id"] not in project_ids:
            problems.append(f"{rid}: unregistered publisher or project")
        uri = urlsplit(row["source_url"])
        if uri.scheme != "https" or uri.query or uri.fragment:
            problems.append(f"{rid}: source link must be canonical https")
        if not (uri.hostname == "onehousing.vn" if row["source_id"] == "onehousing-vn"
                else uri.hostname in ("rever.vn", "blog.rever.vn")):
            problems.append(f"{rid}: incorrect publisher hostname")
        if row.get("asset_type") != "apartment":
            problems.append(f"{rid}: source scope not verified")
        try:
            review = date.fromisoformat(row["review_date"])
            if review > today:
                problems.append(f"{rid}: future review")
            period = row["period"]
            if row.get("period_type") == "month":
                observed = date.fromisoformat(period + "-01")
                if row["source_id"] != "onehousing-vn" or rid != "onehousing-vinhomes-grand-park-apartment-2026-10":
                    problems.append(f"{rid}: unapproved month basis")
                if observed.strftime("%Y-%m") != review.strftime("%Y-%m"):
                    problems.append(f"{rid}: reviewed month mismatch")
            elif row.get("period_type") == "date":
                observed = date.fromisoformat(period)
                if row.get("source_publication_date") != period:
                    problems.append(f"{rid}: dated publisher evidence mismatch")
            else:
                problems.append(f"{rid}: unsupported period type")
                continue
            if observed > review:
                problems.append(f"{rid}: period after review")
        except (ValueError, KeyError):
            problems.append(f"{rid}: invalid dates")
        metric = PRICE.search(row.get("evidence", {}).get("metric", ""))
        if not metric or millions(metric.group(1)) != row.get("value_vnd_per_m2"):
            problems.append(f"{rid}: quoted price doesn't match")
        if not isinstance(row.get("value_vnd_per_m2"), int) or row["value_vnd_per_m2"] <= 0:
            problems.append(f"{rid}: nonpositive/invalid amount")
        bounds = row.get("range_low_vnd_per_m2"), row.get("range_high_vnd_per_m2")
        if row["metric_type"] == "popular-asking-price-per-sqm":
            m = RANGE.search(row.get("evidence", {}).get("range", ""))
            if not m or (millions(m.group(1)), millions(m.group(2))) != bounds:
                problems.append(f"{rid}: publisher price-range evidence mismatch")
            if not all(isinstance(v, int) for v in bounds) or not (bounds[0] <= row["value_vnd_per_m2"] <= bounds[1]):
                problems.append(f"{rid}: inconsistent modal price/range")
            if row["period_type"] != "month" or "10/2026" not in row.get("evidence", {}).get("period", ""):
                problems.append(f"{rid}: missing explicitly dated monthly label")
        elif bounds != (None, None):
            problems.append(f"{rid}: single listing or launch floor is not a range")
        if row["metric_type"].startswith("historical-") and row["period"].startswith("2026-"):
            problems.append(f"{rid}: launch price must remain historical")
        if row["metric_type"] == "single-listing-asking-price-per-sqm" and "69m²" not in row.get("evidence", {}).get("unit", ""):
            problems.append(f"{rid}: missing single-unit context")
        if not row.get("methodology_note"):
            problems.append(f"{rid}: missing methodology")
    if len(seen) != len(LOCKED_LINKS):
        problems.append("unexpected alternative evidence cardinality")
    return problems

def main():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    projects = {x["id"] for x in json.loads(PROJECTS.read_text(encoding="utf-8"))["data"]}
    sources = {x["id"] for x in json.loads(SOURCES.read_text(encoding="utf-8"))["data"]}
    problems = validate(payload["data"], sources, projects, date.today())
    if payload.get("record_count") != len(payload["data"]) or len(payload["data"]) != 4:
        problems.append("bad count")
    if problems:
        raise SystemExit("\n".join(problems))
    print("PASS: 4 alternative source reference facts, 3 projects, 2 publishers; no price history promotion.")

if __name__ == "__main__":
    main()
