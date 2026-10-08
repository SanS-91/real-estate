from pathlib import Path
import importlib.util, json

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("infra_collector",ROOT/"scripts/infrastructure_candidate_collector.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

html=(ROOT/"tests/fixtures/infrastructure_official_update_sample.html").read_text(encoding="utf-8")
row=mod.parse(html,"https://baochinhphu.vn/fixture-infrastructure-update.htm","2026-10-08T00:00:00Z")

assert row["project_id"]=="hcmc-ring-road-3"
assert row["announced_date"]=="2026-10-08"
assert row["project_patch"]["current_progress_percent"]==85.0
assert row["project_patch"]["current_total_investment"]==75300
assert "status" not in row["project_patch"]
assert row["schedule_candidate"]["schedule_type"]=="expected-completion"
assert row["schedule_candidate"]["target_period"]=="2026"
assert row["schedule_candidate"]["date_precision"]=="year"
assert row["source_id"]=="gov-vietnam-infrastructure"
assert row["collector_provenance"]["review_required"] is True
assert mod.validate(row)==[]

schedules=json.loads((ROOT/"data/mock/infrastructure/schedules.json").read_text(encoding="utf-8"))["data"]
assert all(x["status"] in {"current","superseded"} for x in schedules)
assert any(x["status"]=="superseded" for x in schedules)

projects=json.loads((ROOT/"data/mock/infrastructure/projects.json").read_text(encoding="utf-8"))["data"]
ids={x["id"] for x in projects}
assert "hcmc-ring-road-3" in ids

print("Phase 5.7B infrastructure candidate collector tests PASS")
