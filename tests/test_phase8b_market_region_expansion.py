"""Phase 8B: verified geography growth without made-up market price observations."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

regions = read("data/mock/core/regions.json")["data"]
developers = read("data/mock/core/developers.json")["data"]
projects = read("data/mock/market/projects.json")["data"]
sources = read("data/mock/core/sources.json")["data"]
targets = read("config/market-automation-targets.json")["targets"]

by_region = {row["id"]: row for row in regions}
by_project = {row["id"]: row for row in projects}
by_dev = {row["id"]: row for row in developers}
by_source = {row["id"]: row for row in sources}
by_target = {row["target_id"]: row for row in targets}

assert "can-tho" in by_region
assert "can-tho" in by_dev["nam-long"]["region_ids"]
assert by_project["nam-long-ii-central-lake"]["region_ids"] == ["can-tho"]
assert by_project["springville"]["region_ids"] == ["dong-nai"]
assert by_project["nam-long-ii-central-lake"]["total_area_sqm"] == 438000
assert by_project["springville"]["total_area_sqm"] == 182000
assert by_project["springville"]["primary_source_id"] == "gamuda-land-official"
assert by_project["nam-long-ii-central-lake"]["primary_source_id"] == "nam-long-official"

for project_id in ("nam-long-ii-central-lake", "springville"):
    row = by_project[project_id]
    assert by_source[row["primary_source_id"]]["source_type"] == "developer"
    assert row["official_url"].startswith("https://")
    assert row.get("source_review_date") == "2026-10-28"
    assert row.get("source_date") is None, "Do not fake an official publication date"
    assert row.get("planned_units") is None
    assert all(key not in row for key in ("asking_price", "average_asp", "absorption_rate", "sales_units"))

for target_id, project_id in (
    ("nam-long-central-lake-project-official", "nam-long-ii-central-lake"),
    ("gamuda-springville-project-official", "springville"),
):
    target = by_target[target_id]
    assert target["project_id"] == project_id
    assert target["collector"] == "metadata_only" and target["enabled"] is True
    assert target["url"] == by_project[project_id]["official_url"]

parser = (ROOT / "scripts/collectors/namlong_official.py").read_text(encoding="utf-8")
assert '"nam-long-ii-central-lake"' in parser
print("PASS Phase 8B Can Tho and Dong Nai registry expansion with source watches")
