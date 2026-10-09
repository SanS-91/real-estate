"""Adversarial listing evidence: real indexed-source snapshots, no inferred data."""
from __future__ import annotations

import copy
import importlib.util
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("listing_reviewed_batch", ROOT / "scripts/listing_reviewed_batch.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

cfg = json.loads((ROOT / "config/listing-reviewed-captures-20261009.json").read_text(encoding="utf-8"))
production = json.loads((ROOT / "data/mock/market/listing-observations.json").read_text(encoding="utf-8"))["data"]
TODAY = date(2026, 10, 9)
assert len(cfg["records"]) == 4

new, decisions = module.evaluate(cfg["records"], production, TODAY)
assert len(new) == 4, decisions
assert all(d["status"] == "ready" for d in decisions)
assert {x["project_id"] for x in new} == {
    "mizuki-park", "akari-city", "the-privia", "vinhomes-grand-park",
}
assert all(x["source_data_as_of"] <= x["observation_date"] for x in new)
assert all(x["provenance"]["source_access"] == "public-index-only-github-runner-blocked" for x in new)
assert all(x["confidence"] == "reviewed-public-index-snapshot" for x in new)
assert all(x["product_price_ranges"] == [] for x in new)
assert all(x["volatile_metrics"]["use_in_primary_kpi"] is False for x in new)
assert all(x["provenance"]["last_listing_date_is_price_timestamp"] is False for x in new)
assert all(x["market_layer"] == "listing-asking" for x in new)

by_project = {x["project_id"]: x for x in new}
assert (by_project["mizuki-park"]["asking_price_low_vnd_per_m2"], by_project["mizuki-park"]["asking_price_high_vnd_per_m2"]) == (55_800_000, 72_700_000)
assert (by_project["akari-city"]["asking_price_low_vnd_per_m2"], by_project["akari-city"]["asking_price_high_vnd_per_m2"]) == (54_100_000, 64_700_000)
assert by_project["the-privia"]["asking_price_change_1y_pct"] == .048
assert by_project["vinhomes-grand-park"]["asking_price_change_1y_pct"] == -.015
assert by_project["mizuki-park"]["popular_area_low_sqm"] is None

# Only the four newly reviewed projects gain a second independent dated observation.
updated = production + new
series = {}
for row in updated:
    series.setdefault(row["project_id"], set()).add(row["observation_date"])
assert len(updated) == 16, len(updated)
assert len(series) == 12, len(series)
assert sum(len(dates) == 2 for dates in series.values()) == 4
assert sum(len(dates) == 1 for dates in series.values()) == 8
assert sum(len(dates) >= 3 for dates in series.values()) == 0

# Separate original time point from publisher's last listing date and its rolling 1Y trend.
assert by_project["mizuki-park"]["observation_date"] == "2026-10-09"
assert by_project["mizuki-park"]["source_data_as_of"] == "2026-10-07"
assert by_project["mizuki-park"]["asking_price_change_1y_pct"] == .058
assert by_project["mizuki-park"]["asking_price_change_1y_pct"] != .191  # prior portal 1Y metric

# Malicious or unsupported inputs must be stopped before reaching production.
examples = {x["project_id"]: x for x in production}
base = next(x for x in cfg["records"] if x["project_id"] == "akari-city")
for field, wrong, token in (
    ("source_url", "https://example.com/fake", "source-link-does-not-match-project-mapping"),
    ("asking_price_low_vnd_per_m2", 1_000_000, "price-range-does-not-match-source-text"),
    ("asking_price_change_1y_pct", 0.20, "1y-price-trend-does-not-match-source-text"),
    ("source_data_as_of", "2026-08-08", "stale-last-listing-date"),
    ("observation_date", "2026-10-10", "future-review-date"),
    ("listing_count", 9999, "listing-count-does-not-match-source-text"),
):
    altered = copy.deepcopy(base)
    altered[field] = wrong
    problems = module.validate_capture(altered, examples["akari-city"], TODAY)
    assert token in problems, (field, problems)

tampered = copy.deepcopy(base)
tampered["project_id"] = "mizuki-park"
problems = module.validate_capture(tampered, examples["mizuki-park"], TODAY)
assert "source-link-does-not-match-project-mapping" in problems

tampered = copy.deepcopy(base)
tampered["evidence"]["last_listing"] = "Cập nhật tin đăng gần đây nhất | 07-10-2026, 11:30"
assert "last-listing-date-does-not-match-source-text" in module.validate_capture(
    tampered, examples["akari-city"], TODAY
)
tampered = copy.deepcopy(base)
tampered["observation_date"] = "2026-10-08"
assert "not-a-new-snapshot-date" in module.validate_capture(
    tampered, examples["akari-city"], TODAY
)

# Main batch must remain idempotent once a date has been added.
again, decisions = module.evaluate(cfg["records"], updated, TODAY)
assert len(again) == 0
assert all(x["status"] == "unchanged" for x in decisions)

tampered_history = copy.deepcopy(updated)
tampered_history[-1]["asking_price_low_vnd_per_m2"] += 1000000
_, bad_decisions = module.evaluate(cfg["records"], tampered_history, TODAY)
assert any(x["status"] == "manual-review-required" for x in bad_decisions)

print("Reviewed listing capture tests PASS: 4 new sourced snapshots, 12 projects, 0 fabricated trends")
