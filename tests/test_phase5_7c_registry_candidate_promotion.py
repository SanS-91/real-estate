from pathlib import Path
import importlib.util, copy

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("registry_promotion",ROOT/"scripts/registry_candidate_promotion.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Legal: new reviewed candidate can promote; unresolved review issue blocks classification.
legal_prod={"schema_version":1,"data":[{
    "id":"law-31-2024-qh15-land","document_number":"31/2024/QH15","title":"Luật Đất đai",
    "document_type":"law","status":"effective","agency_ids":["national-assembly"],"scope_type":"national",
    "region_ids":[],"topic_ids":["land"],"issued_date":"2024-01-18","effective_date":"2024-08-01",
    "official_url":"https://example.com/land"
}]}
legal_new={
    "id":"candidate-legal-200-2026-nd-cp","document_number":"200/2026/NĐ-CP",
    "title":"Nghị định thử nghiệm","document_type":"decree","status":"effective",
    "agency_ids":["government"],"scope_type":"national","region_ids":[],"topic_ids":["land"],
    "issued_date":"2026-10-05","effective_date":"2026-10-05",
    "official_url":"https://example.com/decree-200","primary_source_id":"gov-vietnam-legal-documents",
    "review_issues":[]
}
dec=mod.legal_preview(legal_prod["data"],[legal_new])
assert dec[0]["status"]=="new"
out,added=mod.promote_legal(legal_prod,[legal_new],dec)
assert added==1
promoted=[x for x in out["data"] if x["document_number"]=="200/2026/NĐ-CP"][0]
assert promoted["id"]=="legal-200-2026-n-d-cp"
assert "review_issues" not in promoted
assert out["record_count"]==2

legal_bad=copy.deepcopy(legal_new); legal_bad["document_number"]="201/2026/NĐ-CP"; legal_bad["review_issues"]=["agency requires review"]
assert mod.legal_preview(legal_prod["data"],[legal_bad])[0]["status"]=="review-required"

# Infrastructure: new schedule supersedes the prior current event and updates current project target.
projects={"schema_version":1,"data":[{
    "id":"hcmc-ring-road-3","name":"Vành đai 3 TPHCM","status":"under-construction",
    "current_expected_completion":"2026-Q4","completion_date_precision":"quarter",
    "current_progress_percent":80,"current_total_investment":75300
}]}
schedules={"schema_version":1,"data":[{
    "id":"schedule-old","infrastructure_project_id":"hcmc-ring-road-3",
    "schedule_type":"expected-completion","target_period":"2026-Q4","date_precision":"quarter",
    "status":"current","announced_date":"2026-08-16","source_id":"hcmc-public-infrastructure",
    "source_url":"https://example.com/old"
}]}
infra_new={
    "id":"candidate-infra-rr3","project_id":"hcmc-ring-road-3","announced_date":"2026-10-08",
    "schedule_candidate":{
        "infrastructure_project_id":"hcmc-ring-road-3","schedule_type":"expected-completion",
        "target_period":"2027-Q1","date_precision":"quarter","announced_date":"2026-10-08",
        "source_id":"gov-vietnam-infrastructure","source_url":"https://example.com/new"
    },
    "project_patch":{"current_progress_percent":85},
    "review_issues":[]
}
idec=mod.infra_preview(projects["data"],schedules["data"],[infra_new])
assert idec[0]["status"]=="new"
np,ns,patched,added_sched=mod.promote_infra(projects,schedules,[infra_new],idec)
assert patched==1 and added_sched==1
assert np["data"][0]["current_progress_percent"]==85
assert np["data"][0]["current_expected_completion"]=="2027-Q1"
assert [x for x in ns["data"] if x["id"]=="schedule-old"][0]["status"]=="superseded"
new_sched=[x for x in ns["data"] if x["id"]!="schedule-old"][0]
assert new_sched["status"]=="current"
assert new_sched["target_period"]=="2027-Q1"

print("Phase 5.7C registry preview/promote tests PASS")
