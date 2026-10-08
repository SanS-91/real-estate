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

# Pipeline contract must work for any valid candidate set, including article-only
# or observation-only staging. Remove candidate keys to simulate pre-promotion.
cand_obs_keys={mod.obs_key(x) for x in cand_obs}
cand_art_keys={mod.article_key(x) for x in cand_art}
pre_obs={**prod_obs,"data":[x for x in prod_obs["data"] if mod.obs_key(x) not in cand_obs_keys]}
pre_obs["record_count"]=len(pre_obs["data"])
pre_art={**prod_art,"data":[x for x in prod_art["data"] if mod.article_key(x) not in cand_art_keys]}
pre_art["record_count"]=len(pre_art["data"])

obs_dec=mod.classify(pre_obs["data"],cand_obs,mod.obs_key,mod.OBS_FIELDS)
art_dec=mod.classify(pre_art["data"],cand_art,mod.article_key,mod.ART_FIELDS)
assert len(obs_dec)==len(cand_obs) and all(x["status"]=="new" for x in obs_dec)
assert len(art_dec)==len(cand_art) and all(x["status"]=="new" for x in art_dec)

new_obs,added_obs=mod.promote_payload(pre_obs,cand_obs,obs_dec,mod.obs_key,"observations")
new_art,added_art=mod.promote_payload(pre_art,cand_art,art_dec,mod.article_key,"articles")
assert added_obs==len(cand_obs)
assert added_art==len(cand_art)
assert new_obs["record_count"]==pre_obs["record_count"]+len(cand_obs)
assert new_art["record_count"]==pre_art["record_count"]+len(cand_art)

# Idempotency: after the simulated promotion, rerunning Preview must classify
# every staged record as unchanged rather than duplicating it.
again_obs=mod.classify(new_obs["data"],cand_obs,mod.obs_key,mod.OBS_FIELDS)
again_art=mod.classify(new_art["data"],cand_art,mod.article_key,mod.ART_FIELDS)
assert all(x["status"]=="unchanged" for x in again_obs)
assert all(x["status"]=="unchanged" for x in again_art)

# Conflict detection works even when the current staging set is article-only.
base_obs=copy.deepcopy((cand_obs or prod_obs["data"])[0])
if base_obs.get("new_supply") is None:
    base_obs["new_supply"]=9999
else:
    base_obs["new_supply"]=base_obs["new_supply"]+1
existing=[copy.deepcopy(base_obs)]
existing[0]["new_supply"]=0 if base_obs["new_supply"]!=0 else 1
d=mod.classify(existing,[base_obs],mod.obs_key,mod.OBS_FIELDS)[0]
assert d["status"]=="conflict"
assert "new_supply" in d["changes"]

print("Phase 5.5F2 market candidate promotion tests PASS")
