from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
load=lambda p: json.loads((ROOT/p).read_text(encoding="utf-8"))

model=load("config/intelligence_model.json")
projects=load("data/mock/market/projects.json")["data"]
regions=load("data/mock/core/regions.json")["data"]
developers=load("data/mock/core/developers.json")["data"]
topics=load("data/mock/legal/topics.json")["data"]
infra=load("data/mock/infrastructure/projects.json")["data"]

assert model["schema_version"]==1
assert set(model["subject_types"])=={"project","region","developer"}
assert model["time_contract"]["inclusive"] is True
assert model["semantics"]["topic_relevance"]
assert model["semantics"]["macro_context"]

project_ids={x["id"] for x in projects}
region_ids={x["id"] for x in regions}
developer_ids={x["id"] for x in developers}
topic_ids={x["id"] for x in topics}
infra_ids={x["id"] for x in infra}

for p in projects:
    assert set(p.get("region_ids",[])) <= region_ids, (p["id"],"region")
    assert set(p.get("developer_ids",[])) <= developer_ids, (p["id"],"developer")
    if p.get("lead_developer_id"):
        assert p["lead_developer_id"] in developer_ids
    assert set(p.get("related_legal_topic_ids",[])) <= topic_ids, (p["id"],"legal-topic")
    assert set(p.get("related_infrastructure_ids",[])) <= infra_ids, (p["id"],"infrastructure")

for x in infra:
    assert set(x.get("region_ids",[])) <= region_ids, (x["id"],"region")
    assert set(x.get("related_real_estate_project_ids",[])) <= project_ids, (x["id"],"project")

for name,contract in model["evidence_contract"].items():
    assert (ROOT/contract["dataset"]).exists(), (name,contract["dataset"])

print("Phase 6.0 intelligence model contract tests PASS")
