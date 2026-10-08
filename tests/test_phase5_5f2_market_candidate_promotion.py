from pathlib import Path
import importlib.util, json, copy

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("market_promotion",ROOT/"scripts/market_candidate_promotion.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

prod_obs=json.loads((ROOT/"data/mock/market/observations.json").read_text(encoding="utf-8"))
prod_art=json.loads((ROOT/"data/mock/articles/articles.json").read_text(encoding="utf-8"))
cand_obs=json.loads((ROOT/"data/candidate/market/observations.json").read_text(encoding="utf-8"))["data"]
cand_art=json.loads((ROOT/"data/candidate/market/articles.json").read_text(encoding="utf-8"))["data"]

assert mod.validate_observations(cand_obs)==[]
assert mod.validate_articles(cand_art)==[]

obs_dec=mod.classify(prod_obs["data"],cand_obs,mod.obs_key,mod.OBS_FIELDS)
art_dec=mod.classify(prod_art["data"],cand_art,mod.article_key,mod.ART_FIELDS)

assert len(obs_dec)==1 and obs_dec[0]["status"]=="new"
assert len(art_dec)==2 and all(x["status"]=="new" for x in art_dec)

new_obs,added_obs=mod.promote_payload(prod_obs,cand_obs,obs_dec,mod.obs_key,"observations")
new_art,added_art=mod.promote_payload(prod_art,cand_art,art_dec,mod.article_key,"articles")
assert added_obs==1
assert added_art==2
assert new_obs["record_count"]==prod_obs["record_count"]+1
assert new_art["record_count"]==prod_art["record_count"]+2
assert any(x["id"]=="obs-hcmc-landed-2026-q2-cbre" and x["new_supply"]==1934 for x in new_obs["data"])
assert any(x["id"]=="article-market-nam-long-akari-jv-update-2026-10-02" for x in new_art["data"])

conflict=copy.deepcopy(cand_obs[0]); conflict["new_supply"]=9999
d=mod.classify(prod_obs["data"]+[cand_obs[0]],[conflict],mod.obs_key,mod.OBS_FIELDS)[0]
assert d["status"]=="conflict"
assert d["changes"]["new_supply"]["from"]==1934

print("Phase 5.5F2 market candidate promotion tests PASS")
