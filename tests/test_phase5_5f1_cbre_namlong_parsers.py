from pathlib import Path
import importlib.util, json, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

from collectors import cbre_market, namlong_official

cbre=(ROOT/"tests/fixtures/cbre_hcmc_q2_2026.html").read_text(encoding="utf-8")
rows=cbre_market.parse(cbre,"https://example.com/cbre","2026-10-08T00:00:00Z")
by={x["segment_id"]:x for x in rows}
assert by["apartment"]["new_supply"]==850
assert by["landed"]["new_supply"]==1934

nlg=(ROOT/"tests/fixtures/namlong_project_update_2026.html").read_text(encoding="utf-8")
article=namlong_official.parse_article(nlg,"https://example.com/namlong","2026-10-08T00:00:00Z")
assert article["published_date"]=="2026-10-02"
assert {"waterpoint","mizuki-park","akari-city","izumi-city"}.issubset(set(article["project_ids"]))
facts={x["type"]:x for x in article["facts"]}
assert facts["developer-stated-sales"]["units"]==3500
assert facts["developer-stated-sales"]["absorption_rate"]==1.0
assert facts["certificate-progress"]["household_pct"]==0.97

spec=importlib.util.spec_from_file_location("candidate",ROOT/"scripts/market_source_candidate_collector.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

target={
 "target_id":"cbre-hcmc-q2-2026",
 "observation_source_id":"cbre-vietnam-market"
}
built=mod.build_cbre_rows(target,rows,"https://example.com/cbre")
assert len(built)==2
assert {x["segment_ids"][0] for x in built}=={"apartment","landed"}
assert {x["new_supply"] for x in built}=={850,1934}
assert all(x["source_id"]=="cbre-vietnam-market" for x in built)

nltarget={"target_id":"nam-long-akari-jv-update-2026-10-02","period":"2026-10-02"}
a=mod.build_namlong_article(nltarget,article,"https://example.com/namlong")
assert a["source_id"]=="nam-long-official"
assert a["content_type"]=="developer-update"
assert "akari-city" in a["project_ids"]
assert a["structured_facts"][0]["type"]=="developer-stated-sales"

prod_obs=json.loads((ROOT/"data/mock/market/observations.json").read_text(encoding="utf-8"))["data"]
keys={mod.existing_obs_key(x):x for x in prod_obs}
ap=[x for x in built if x["segment_ids"]==["apartment"]][0]
land=[x for x in built if x["segment_ids"]==["landed"]][0]
assert mod.existing_obs_key(ap) in keys
assert keys[mod.existing_obs_key(ap)]["new_supply"]==850
assert mod.existing_obs_key(land) not in keys

print("Phase 5.5F1 CBRE + Nam Long parser tests PASS")
