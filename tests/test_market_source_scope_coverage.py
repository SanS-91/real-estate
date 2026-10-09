"""Market coverage round 3: correct product category, no cross-scope leakage."""
from __future__ import annotations

import copy
import importlib.util
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

gate = module("listing_scope_evidence_gate")
monitor = module("listing_monitor_health")

scoped_payload = json.loads((ROOT / "data/mock/market/listing-scope-evidence.json").read_text(encoding="utf-8"))
scope = scoped_payload["data"]
listing = json.loads((ROOT / "data/mock/market/listing-observations.json").read_text(encoding="utf-8"))["data"]
projects = {x["id"] for x in json.loads((ROOT / "data/mock/market/projects.json").read_text(encoding="utf-8"))["data"]}
today = date(2026, 10, 9)

assert len(scope) == scoped_payload["record_count"] == 4
assert len({x["project_id"] for x in scope}) == 4
assert not gate.check(scope, listing, projects, today)

refs = {x["project_id"]: x for x in scope}
izumi = refs["izumi-city"]
essensia = refs["essensia-parkway"]

assert izumi["price_scope"] == "landed-only"
assert izumi["asset_type"] == "villa-townhouse"
assert (izumi["asking_price_low_vnd_per_m2"], izumi["asking_price_high_vnd_per_m2"]) == (54_500_000, 83_500_000)
assert izumi["asking_price_change_1y_pct"] == 0.14
assert "source-has-unrelated" in izumi["data_quality_flag"]
assert "/ban-nha-biet-thu-lien-ke-izumi-city" in izumi["source_url"]
assert essensia["price_scope"] == "landed-only"
assert (essensia["asking_price_low_vnd_per_m2"], essensia["asking_price_high_vnd_per_m2"]) == (196_100_000, 225_000_000)
assert essensia["asking_price_change_1y_pct"] == -0.05
assert "/ban-nha-biet-thu-lien-ke-essensia-parkway" in essensia["source_url"]

by_project = {x["project_id"]: x for x in sorted(listing, key=lambda o: (o["project_id"], o["observation_date"]))}
assert len(listing) == 18
assert all(by_project[pid]["asking_price_low_vnd_per_m2"] is None for pid in refs)
assert by_project["izumi-city"]["asset_type"] == "apartment"  # original misleading portal mapping stays historical
assert by_project["essensia-parkway"]["asset_type"] == "villa-townhouse-shophouse"

for pid in ("izumi-city", "essensia-parkway"):
    row = refs[pid]
    for field, wrong in [
        ("price_scope", "apartment-only"),
        ("asset_type", "apartment"),
        ("source_url", "https://badactor.invalid/price"),
        ("asking_price_high_vnd_per_m2", 999999999),
        ("review_date", "2026-10-20"),
    ]:
        tampered = copy.deepcopy(row)
        tampered[field] = wrong
        test = copy.deepcopy(scope)
        test[test.index(row)] = tampered
        assert gate.check(test, listing, projects, today), (pid, field)
tampered = copy.deepcopy(scope)
next(x for x in tampered if x["project_id"] == "izumi-city")["data_quality_flag"] = None
assert any("mismatch" in x for x in gate.check(tampered, listing, projects, today))

report = monitor.build(listing, {
    "source_access": "blocked", "generated_at": "2026-10-09T03:57:47Z",
    "projects_checked": 12, "candidate_records": 0,
    "projects": [{"project_id": pid, "status": "http-error"} for pid in projects],
}, today, scope)
assert report["projects_tracked"] == 12
assert report["aggregate_priced_projects"] == 8
assert report["project_level_price_missing"] == 4
assert report["category_reference_projects"] == 4
assert report["category_reference_count"] == 4
assert report["projects_with_2plus_snapshots"] == 6
assert report["source_access"] == "blocked"
assert report["source_checks"] == 12
assert report["source_candidate_records"] == 0
assert report["no_new_price_inferred"] is True
assert report["priority_backlog"][0]["project_id"] in refs
assert all(x["project_price_coverage"] == "partial" for x in report["priority_backlog"][:4])
assert all(x["category_reference_count"] == 1 for x in report["priority_backlog"][:4])

published = json.loads((ROOT / "data/state/listing-source-coverage.json").read_text(encoding="utf-8"))
assert published["schema_version"] == 2
assert published["aggregate_priced_projects"] == 8
assert published["category_reference_projects"] == 4
assert published["project_level_price_missing"] == 4
assert published["no_new_price_inferred"] is True

js = (ROOT / "assets/js/market.js").read_text(encoding="utf-8")
assert "function listingScopeDescription(row)" in js
assert "function marketListingCoverageSummary()" in js
assert "review-project-aggregate-with-correct-product-class" in (ROOT / "scripts/listing_monitor_health.py").read_text(encoding="utf-8")
assert "DataStore.getListingSourceCoverage().catch(() => null)" in js
assert "filteredProjects.some(project=>project.id === row.project_id)" in js
assert "Không sử dụng để tính giá căn hộ Izumi" in js
print("PASS: 4 category-specific, non-chartable evidence records; 8/12 aggregate; 6 with 2 captures; blocked collection disclosed.")
