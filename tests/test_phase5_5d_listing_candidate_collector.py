from pathlib import Path
import copy
import importlib.util
import json

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("collector", ROOT/"scripts/listing_candidate_collector.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

html_full="""
<html><body>
<h1>Mizuki Park</h1>
<div>Khoảng giá 57,5 - 73 triệu/m²</div>
<div>Biến động giá 1 năm 19,1%</div>
<div>Diện tích phổ biến 56 - 107 m²</div>
<div>267 BĐS đang bán</div>
<div>3.517 lượt xem trong 7 ngày qua</div>
</body></html>
"""
parsed=mod.parse_listing_page(html_full)
assert parsed["asking_price_low_vnd_per_m2"]==57_500_000
assert parsed["asking_price_high_vnd_per_m2"]==73_000_000
assert parsed["asking_price_change_1y_pct"]==0.191
assert parsed["popular_area_low_sqm"]==56
assert parsed["popular_area_high_sqm"]==107
assert parsed["listing_count"]==267
assert parsed["project_views_7d"]==3517
assert all(parsed["evidence"].values())

html_partial="""
<html><body>
<h1>Celesta Gold</h1>
<div>Diện tích phổ biến 47 - 105 m²</div>
<div>6 BĐS</div>
</body></html>
"""
partial=mod.parse_listing_page(html_partial)
assert partial["asking_price_low_vnd_per_m2"] is None
assert partial["popular_area_low_sqm"]==47
assert partial["listing_count"]==6

prod=json.loads((ROOT/"data/mock/market/listing-observations.json").read_text(encoding="utf-8"))
# Fixture captures originally compared against the 08 Oct baseline, not current history.
prod["data"]=[x for x in prod["data"] if x.get("observation_date")=="2026-10-08"]
by={x["project_id"]:x for x in prod["data"]}

miz=by["mizuki-park"]
same=mod.build_candidate(miz, parsed, "2026-10-09")
assert same is not None
assert same["observation_date"]=="2026-10-09"
assert same["confidence"]=="auto-candidate-unreviewed"
assert mod.comparable_primary(miz, parsed)

changed=copy.deepcopy(parsed)
changed["asking_price_high_vnd_per_m2"]=74_000_000
candidate=mod.build_candidate(miz, changed, "2026-10-09")
assert candidate["asking_price_high_vnd_per_m2"]==74_000_000
assert not mod.comparable_primary(miz, changed)

# A full source that suddenly loses its price range must be held as degraded.
degraded=copy.deepcopy(parsed)
degraded["asking_price_low_vnd_per_m2"]=None
degraded["asking_price_high_vnd_per_m2"]=None
assert mod.build_candidate(miz, degraded, "2026-10-09") is None

# A partial source may remain partial and must not invent an aggregate range.
celesta=by["celesta-gold"]
partial_candidate=mod.build_candidate(celesta, partial, "2026-10-09")
assert partial_candidate is not None
assert partial_candidate["coverage_status"]=="partial"
assert partial_candidate["asking_price_low_vnd_per_m2"] is None

assert mod.int_loose("3.517")==3517
assert mod.number_vi("19,1")==19.1
print("Phase 5.5D listing candidate collector tests PASS")

collector_source=(ROOT/"scripts/listing_candidate_collector.py").read_text(encoding="utf-8")
assert '"source_access": source_access' in collector_source
assert 'counts.get("http-error", 0) == len(rows)' in collector_source
print("Phase 5.5D source access status guards PASS")
