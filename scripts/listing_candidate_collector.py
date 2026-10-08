from __future__ import annotations

from pathlib import Path
import argparse
import copy
import json
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "data/mock/market/listing-observations.json"
CANDIDATE = ROOT / "data/candidate/market/listing-observations.json"
REPORT = ROOT / "data/candidate/market/listing-collector-report.json"

UA = "Mozilla/5.0 (compatible; RealEstateMarketIntelligence/1.0; +https://github.com/SanS-91/real-estate)"
TIMEOUT = 20
DELAY_SECONDS = 1.5

PRICE_PATTERNS = [
    re.compile(r"(?:Khoảng giá|Giá phổ biến|Mức giá)[^\d]{0,80}(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*(?:triệu|tr)\s*/?\s*m(?:²|2)", re.I),
    re.compile(r"(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*(?:triệu|tr)\s*/?\s*m(?:²|2)", re.I),
]
TREND_PATTERNS = [
    re.compile(r"(?:Biến động|Thay đổi|Giá.*?1 năm|1 năm)[^\d+\-]{0,80}([+\-−]?\d+(?:[.,]\d+)?)\s*%", re.I),
    re.compile(r"([+\-−]?\d+(?:[.,]\d+)?)\s*%[^\n]{0,60}(?:1 năm|12 tháng)", re.I),
]
AREA_PATTERNS = [
    re.compile(r"(?:Diện tích phổ biến|Diện tích)[^\d]{0,80}(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*m(?:²|2)", re.I),
]
LISTING_COUNT_PATTERNS = [
    re.compile(r"(\d[\d.,]*)\s*(?:BĐS|bất động sản|tin đăng)", re.I),
]
VIEWS_PATTERNS = [
    re.compile(r"(\d[\d.,]*)\s*lượt xem[^\n]{0,80}(?:7 ngày|7 ngày qua)", re.I),
]

def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def number_vi(value: str) -> float:
    value = value.strip().replace("−", "-")
    if "," in value and "." in value:
        # Vietnamese thousands separators are often dots and decimal comma.
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    return float(value)

def int_loose(value: str) -> int:
    return int(re.sub(r"[^0-9]", "", value or "") or "0")

def extract_first(text: str, patterns):
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match
    return None

def html_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script","style","noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return re.sub(r"[ \t]+", " ", text)

def parse_listing_page(html: str) -> dict:
    text = html_text(html)

    price = extract_first(text, PRICE_PATTERNS)
    low = high = None
    if price:
        low = int(round(number_vi(price.group(1)) * 1_000_000))
        high = int(round(number_vi(price.group(2)) * 1_000_000))
        if low > high:
            low, high = high, low

    trend = extract_first(text, TREND_PATTERNS)
    trend_pct = number_vi(trend.group(1)) / 100 if trend else None

    area = extract_first(text, AREA_PATTERNS)
    area_low = area_high = None
    if area:
        area_low = number_vi(area.group(1))
        area_high = number_vi(area.group(2))
        if area_low > area_high:
            area_low, area_high = area_high, area_low

    count = extract_first(text, LISTING_COUNT_PATTERNS)
    views = extract_first(text, VIEWS_PATTERNS)

    return {
        "asking_price_low_vnd_per_m2": low,
        "asking_price_high_vnd_per_m2": high,
        "asking_price_change_1y_pct": trend_pct,
        "popular_area_low_sqm": area_low,
        "popular_area_high_sqm": area_high,
        "listing_count": int_loose(count.group(1)) if count else None,
        "project_views_7d": int_loose(views.group(1)) if views else None,
        "evidence": {
            "price_range_found": bool(price),
            "trend_found": bool(trend),
            "area_found": bool(area),
            "listing_count_found": bool(count),
            "views_found": bool(views),
        },
    }

def latest_rows(rows: list[dict]) -> dict[str, dict]:
    latest = {}
    for row in sorted(rows, key=lambda x: (x.get("project_id") or "", x.get("observation_date") or "")):
        latest[row["project_id"]] = row
    return latest

def comparable_primary(row: dict, parsed: dict) -> tuple:
    return (
        row.get("asking_price_low_vnd_per_m2"),
        row.get("asking_price_high_vnd_per_m2"),
        row.get("asking_price_change_1y_pct"),
        row.get("popular_area_low_sqm"),
        row.get("popular_area_high_sqm"),
    ) == (
        parsed.get("asking_price_low_vnd_per_m2"),
        parsed.get("asking_price_high_vnd_per_m2"),
        parsed.get("asking_price_change_1y_pct"),
        parsed.get("popular_area_low_sqm"),
        parsed.get("popular_area_high_sqm"),
    )

def build_candidate(previous: dict, parsed: dict, observation_date: str) -> dict | None:
    # Partial mapped pages are only refreshed when we can preserve/upgrade evidence quality safely.
    has_range = parsed["asking_price_low_vnd_per_m2"] is not None and parsed["asking_price_high_vnd_per_m2"] is not None
    if previous.get("coverage_status") == "full" and not has_range:
        return None

    coverage = "full" if has_range else "partial"
    candidate = copy.deepcopy(previous)
    candidate["id"] = f"bdsc-{previous['project_id']}-{observation_date}"
    candidate["observation_date"] = observation_date
    candidate["source_data_as_of"] = observation_date
    candidate["coverage_status"] = coverage

    for field in (
        "asking_price_low_vnd_per_m2",
        "asking_price_high_vnd_per_m2",
        "asking_price_change_1y_pct",
        "popular_area_low_sqm",
        "popular_area_high_sqm",
    ):
        candidate[field] = parsed.get(field)

    candidate["volatile_metrics"] = {
        "listing_count": parsed.get("listing_count"),
        "project_views_7d": parsed.get("project_views_7d"),
        "use_in_primary_kpi": False,
        "note": "Automatically extracted candidate only; volatile portal counts/views remain ancillary until reviewed.",
    }
    candidate["methodology_note"] = (
        "Automatically extracted Batdongsan.com.vn candidate snapshot. "
        "Requires validation before promotion. Asking/listing values are not transaction prices or official sales."
    )
    candidate["confidence"] = "auto-candidate-unreviewed"
    candidate["status"] = "candidate"
    return candidate

def fetch(session: requests.Session, url: str) -> tuple[int, str, str]:
    response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
    return response.status_code, response.url, response.text

def collect(observation_date: str, project_filter: set[str] | None = None) -> tuple[list[dict], list[dict]]:
    production = read_json(PRODUCTION, {"data":[]})
    latest = latest_rows(production.get("data", []))
    session = requests.Session()
    session.headers.update({
        "User-Agent": UA,
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.6",
    })

    candidates = []
    report = []
    for project_id, previous in sorted(latest.items()):
        if project_filter and project_id not in project_filter:
            continue
        url = previous.get("source_url")
        if not url or urlparse(url).netloc not in {"batdongsan.com.vn", "www.batdongsan.com.vn"}:
            report.append({"project_id":project_id,"status":"skipped-invalid-url","url":url})
            continue

        try:
            status_code, final_url, html = fetch(session, url)
            if status_code != 200:
                report.append({"project_id":project_id,"status":"http-error","http_status":status_code,"url":url,"final_url":final_url})
                continue
            parsed = parse_listing_page(html)
            candidate = build_candidate(previous, parsed, observation_date)
            if candidate is None:
                report.append({"project_id":project_id,"status":"degraded-no-range","url":url,"final_url":final_url,"evidence":parsed["evidence"]})
                continue

            changed = not comparable_primary(previous, parsed)
            # Candidate file should remain concise: keep rows with primary changes.
            # Volatile listing counts/views are reported but do not alone trigger a candidate.
            if changed:
                candidates.append(candidate)
                status = "candidate-changed"
            else:
                status = "unchanged-primary"

            report.append({
                "project_id":project_id,
                "status":status,
                "url":url,
                "final_url":final_url,
                "coverage_status":candidate["coverage_status"],
                "evidence":parsed["evidence"],
                "asking_price_low_vnd_per_m2":parsed["asking_price_low_vnd_per_m2"],
                "asking_price_high_vnd_per_m2":parsed["asking_price_high_vnd_per_m2"],
                "asking_price_change_1y_pct":parsed["asking_price_change_1y_pct"],
                "popular_area_low_sqm":parsed["popular_area_low_sqm"],
                "popular_area_high_sqm":parsed["popular_area_high_sqm"],
                "listing_count":parsed["listing_count"],
                "project_views_7d":parsed["project_views_7d"],
            })
        except Exception as exc:
            report.append({"project_id":project_id,"status":"fetch-error","url":url,"error":str(exc)[:300]})
        time.sleep(DELAY_SECONDS)

    return candidates, report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat())
    parser.add_argument("--project", action="append", default=[])
    parser.add_argument("--html-file")
    parser.add_argument("--base-project")
    args = parser.parse_args()

    if args.html_file:
        parsed = parse_listing_page(Path(args.html_file).read_text(encoding="utf-8"))
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        return

    candidates, rows = collect(args.date, set(args.project) if args.project else None)
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "observation_date": args.date,
        "record_count": len(candidates),
        "data": candidates,
    }
    report = {
        "generated_at": payload["generated_at"],
        "observation_date": args.date,
        "projects_checked": len(rows),
        "candidate_records": len(candidates),
        "counts": {status: sum(1 for x in rows if x["status"] == status) for status in sorted({x["status"] for x in rows})},
        "projects": rows,
    }
    write_json(CANDIDATE, payload)
    write_json(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
