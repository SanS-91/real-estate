from pathlib import Path
import copy, importlib.util, json

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("listing_pipeline", ROOT/"scripts/listing_snapshot_pipeline.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

prod=json.loads((ROOT/"data/mock/market/listing-observations.json").read_text(encoding="utf-8"))
assert prod["record_count"]==len(prod["data"])>=12
base={x["project_id"]:x for x in sorted(prod["data"],key=lambda x:(x["project_id"],x["observation_date"]))}["akari-city"]

same=copy.deepcopy(base)
same["id"]="bdsc-akari-city-2026-10-18"
same["observation_date"]="2026-10-18"
assert mod.validate([same])==[]
d=mod.classify(prod["data"],[same])[0]
assert d["status"]=="new-unchanged"

changed=copy.deepcopy(same)
changed["id"]="bdsc-akari-city-2026-10-19"
changed["observation_date"]="2026-10-19"
changed["asking_price_high_vnd_per_m2"]=67_000_000
d2=mod.classify(prod["data"],[changed])[0]
assert d2["status"]=="new-changed"
assert d2["changes"]["asking_price_high_vnd_per_m2"]["from"]==base["asking_price_high_vnd_per_m2"]

conflict=copy.deepcopy(base)
conflict["asking_price_low_vnd_per_m2"]=1
d3=mod.classify(prod["data"],[conflict])[0]
assert d3["status"]=="conflict"

promoted,added=mod.promote(prod,[same],[d])
assert added==1
assert promoted["record_count"]==prod["record_count"]+1
assert prod["record_count"]==len(prod["data"])
assert len({mod.logical_key(x) for x in promoted["data"]})==promoted["record_count"]

partial=copy.deepcopy(base)
partial["id"]="bad-partial"
partial["project_id"]="izumi-city"
partial["observation_date"]="2026-10-09"
partial["coverage_status"]="partial"
partial["asking_price_low_vnd_per_m2"]=10
partial["asking_price_high_vnd_per_m2"]=None
assert any("both present or both blank" in x for x in mod.validate([partial]))

print("Phase 5.5C listing snapshot pipeline tests PASS")
