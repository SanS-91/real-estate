from __future__ import annotations

from pathlib import Path
import argparse
import copy
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "data/mock/market/listing-observations.json"
CANDIDATE = ROOT / "data/candidate/market/listing-observations.json"
ASSISTED_REPORT = ROOT / "data/candidate/market/listing-assisted-report.json"
SOURCE_REGISTRY = ROOT / "config/market-source-registry.json"


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def latest_by_project(rows: list[dict]) -> dict[str, dict]:
    latest = {}
    for row in sorted(rows, key=lambda x: (x.get("project_id") or "", x.get("observation_date") or "")):
        latest[row["project_id"]] = row
    return latest


def listing_sources() -> dict[str, dict]:
    registry = read_json(SOURCE_REGISTRY, {"sources":[]})
    return {
        x["source_id"]: x
        for x in registry.get("sources", [])
        if "listing-asking" in (x.get("supported_layers") or [])
    }


def parse_optional_number(value: str | None, scale: float = 1.0):
    if value is None or str(value).strip() == "":
        return None
    return float(str(value).replace(",", ".")) * scale


def parse_optional_int(value: str | None, scale: int = 1):
    number = parse_optional_number(value, scale)
    return int(round(number)) if number is not None else None


def build_candidate(previous: dict, args) -> dict:
    candidate = copy.deepcopy(previous)
    candidate["id"] = f"{args.source_id}-{args.project_id}-{args.date}"
    candidate["source_id"] = args.source_id
    candidate["source_url"] = args.source_url
    candidate["observation_date"] = args.date
    candidate["source_data_as_of"] = args.source_data_as_of or args.date
    candidate["market_layer"] = "listing-asking"

    lo = parse_optional_int(args.price_low_mn, 1_000_000)
    hi = parse_optional_int(args.price_high_mn, 1_000_000)
    if (lo is None) != (hi is None):
        raise SystemExit("price_low_mn and price_high_mn must be both filled or both blank")
    if lo is not None and lo > hi:
        lo, hi = hi, lo

    trend = parse_optional_number(args.trend_pct, 0.01)
    area_lo = parse_optional_number(args.area_low_sqm)
    area_hi = parse_optional_number(args.area_high_sqm)
    if (area_lo is None) != (area_hi is None):
        raise SystemExit("area_low_sqm and area_high_sqm must be both filled or both blank")
    if area_lo is not None and area_lo > area_hi:
        area_lo, area_hi = area_hi, area_lo

    candidate["asking_price_low_vnd_per_m2"] = lo
    candidate["asking_price_high_vnd_per_m2"] = hi
    candidate["asking_price_change_1y_pct"] = trend
    candidate["popular_area_low_sqm"] = area_lo
    candidate["popular_area_high_sqm"] = area_hi
    candidate["coverage_status"] = "full" if lo is not None else "partial"
    candidate["product_price_ranges"] = []

    candidate["volatile_metrics"] = {
        "listing_count": parse_optional_int(args.listing_count),
        "project_views_7d": parse_optional_int(args.views_7d),
        "use_in_primary_kpi": False,
        "note": "Assisted snapshot; portal counts/views are ancillary and do not independently justify a history point.",
    }
    candidate["methodology_note"] = (
        "Human-assisted source-backed listing snapshot. Values represent advertised asking/listing market, "
        "not executed transaction price, official developer sales, or absorption."
    )
    candidate["confidence"] = "assisted-reviewed-input"
    candidate["status"] = "candidate"
    candidate["provenance"] = {
        "capture_mode": "assisted-browser",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "review_required": True,
        "source_data_as_of": candidate["source_data_as_of"],
    }
    return candidate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--source-id", default="batdongsan-com-vn")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--date", default=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat())
    parser.add_argument("--source-data-as-of")
    parser.add_argument("--price-low-mn")
    parser.add_argument("--price-high-mn")
    parser.add_argument("--trend-pct")
    parser.add_argument("--area-low-sqm")
    parser.add_argument("--area-high-sqm")
    parser.add_argument("--listing-count")
    parser.add_argument("--views-7d")
    args = parser.parse_args()

    sources = listing_sources()
    if args.source_id not in sources:
        raise SystemExit(f"source_id {args.source_id!r} is not registered for listing-asking")
    host = urlparse(args.source_url).netloc.lower()
    if not host:
        raise SystemExit("source_url must be an absolute URL")

    production = read_json(PRODUCTION, {"data":[]})
    latest = latest_by_project(production.get("data", []))
    previous = latest.get(args.project_id)
    if not previous:
        raise SystemExit(f"Unknown project_id or no prior listing mapping: {args.project_id}")

    candidate = build_candidate(previous, args)
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "observation_date": args.date,
        "record_count": 1,
        "data": [candidate],
    }
    report = {
        "generated_at": payload["generated_at"],
        "project_id": args.project_id,
        "source_id": args.source_id,
        "source_role": sources[args.source_id].get("source_role"),
        "capture_mode": sources[args.source_id].get("access_mode"),
        "source_url": args.source_url,
        "observation_date": args.date,
        "source_data_as_of": candidate["source_data_as_of"],
        "coverage_status": candidate["coverage_status"],
        "candidate_file": str(CANDIDATE.relative_to(ROOT)),
        "production_written": False,
    }
    write_json(CANDIDATE, payload)
    write_json(ASSISTED_REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
