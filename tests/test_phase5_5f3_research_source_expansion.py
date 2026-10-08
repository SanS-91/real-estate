from pathlib import Path
import importlib.util, json, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

from collectors import cushman_market, jll_research, savills_research

cw=(ROOT/"tests/fixtures/cushman_hcmc_residential_q2_2026.html").read_text(encoding="utf-8")
rows=cushman_market.parse(cw,"https://example.com/cw","2026-10-08T00:00:00Z")
by={x["segment_id"]:x for x in rows}
assert by["apartment"]["new_supply"] is None
assert by["apartment"]["lower_bound_new_supply"]==1300
assert by["apartment"]["absorption_rate"]==0.31
assert by["landed"]["new_supply"]==1700
assert by["landed"]["sales_units"]==870
assert by["landed"]["absorption_rate"]==0.36
ca=cushman_market.parse_article(cw,"https://example.com/cw","2026-10-08T00:00:00Z")
assert ca["published_date"]=="2026-08-01"
assert "Apartment new supply exceeded 1,300 units" in ca["summary"]
assert "landed absorption was about 36%" in ca["summary"]

jll=(ROOT/"tests/fixtures/jll_hcmc_residential_q2_2026.html").read_text(encoding="utf-8")
ja=jll_research.parse_article(jll,"https://example.com/jll","2026-10-08T00:00:00Z")
assert ja["published_date"]=="2026-08-25"
assert "stable in Q2 2026" in ja["summary"]
assert "interest rate pressures" in ja["summary"]

sav=(ROOT/"tests/fixtures/savills_vietnam_q2_2026.html").read_text(encoding="utf-8")
sa=savills_research.parse_article(sav,"https://example.com/savills","2026-10-08T00:00:00Z")
assert sa["published_date"]=="2026-08-12"
assert "Q2/2026" in sa["title"]

spec=importlib.util.spec_from_file_location("candidate",ROOT/"scripts/market_source_candidate_collector.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cw_target={"target_id":"cushman-hcmc-residential-q2-2026","observation_source_id":"cushman-wakefield-vietnam-market","period":"2026-Q2","period_type":"quarter","scope":"hcmc-residential"}
built=mod.build_cushman_rows(cw_target,rows,"https://example.com/cw")
assert len(built)==2
assert {x["segment_ids"][0] for x in built}=={"apartment","landed"}
assert all(x["source_id"]=="cushman-wakefield-vietnam-market" for x in built)
assert [x for x in built if x["segment_ids"]==["apartment"]][0]["new_supply"] is None

jll_target={"target_id":"jll-hcmc-residential-q2-2026","observation_source_id":"jll-vietnam-market","period":"2026-Q2","period_type":"quarter","scope":"hcmc-residential"}
jr=mod.build_research_article(jll_target,ja,"https://example.com/jll")
assert jr["source_id"]=="jll-vietnam-market"
assert jr["content_type"]=="research"
assert jr["region_ids"]==["hcmc"]

sav_target={"target_id":"savills-vietnam-q2-2026-market-brief","observation_source_id":"savills-vietnam-market","period":"2026-Q2","period_type":"quarter","scope":"vietnam-market-research"}
sr=mod.build_research_article(sav_target,sa,"https://example.com/savills")
assert sr["source_id"]=="savills-vietnam-market"
assert sr["published_at"].startswith("2026-08-12")

sources=json.loads((ROOT/"data/mock/core/sources.json").read_text(encoding="utf-8"))["data"]
source_ids={x["id"] for x in sources}
assert {"jll-vietnam-market","cushman-wakefield-vietnam-market","savills-vietnam-market"} <= source_ids

print("Phase 5.5F3 research source expansion tests PASS")
