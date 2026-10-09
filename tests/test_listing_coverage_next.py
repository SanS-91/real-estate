from __future__ import annotations
import copy
import importlib.util
import json
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/(name+".py"))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

batch=script("listing_reviewed_batch")
scope=script("listing_scope_evidence_gate")
report=script("build_history_coverage")
today=date(2026,10,9)
config=json.loads((ROOT/"config/listing-reviewed-captures-20261009-part2.json").read_text())
rows=json.loads((ROOT/"data/mock/market/listing-observations.json").read_text())["data"]
projects={x["id"] for x in json.loads((ROOT/"data/mock/market/projects.json").read_text())["data"]}
scoped=json.loads((ROOT/"data/mock/market/listing-scope-evidence.json").read_text())["data"]
pre=[r for r in rows if not (r["project_id"] in ("waterpoint","eaton-park") and r["observation_date"]=="2026-10-09")]

assert len(config["records"])==2
assert len(pre)==16
new,decisions=batch.evaluate(config["records"],pre,today)
assert len(new)==2,decisions
assert all(x["status"]=="ready" for x in decisions)
by={x["project_id"]:x for x in new}
assert by["waterpoint"]["asset_type"]=="villa-townhouse"
assert by["waterpoint"]["asking_price_low_vnd_per_m2"]==38200000
assert by["waterpoint"]["asking_price_high_vnd_per_m2"]==60200000
assert by["waterpoint"]["asking_price_change_1y_pct"]==-.066
assert by["eaton-park"]["asset_type"]=="apartment"
assert by["eaton-park"]["asking_price_low_vnd_per_m2"]==126900000
assert by["eaton-park"]["asking_price_high_vnd_per_m2"]==188600000
assert by["eaton-park"]["asking_price_change_1y_pct"]==-.045

# Avoid cloning another date that has the same price data: no synthetic trend.
copy_same=copy.deepcopy(config["records"][0])
copy_same["observation_date"]="2026-10-10"
prior=next(x for x in pre if x["project_id"]=="waterpoint")
assert "future-review-date" in batch.validate_capture(copy_same,prior,today)
bad=copy.deepcopy(config["records"][0])
bad["asking_price_change_1y_pct"]=.066
assert "1y-price-trend-does-not-match-source-text" in batch.validate_capture(bad,prior,today)

with_data=pre+new
by_day={}
for item in with_data:
    by_day.setdefault(item["project_id"],set()).add(item["observation_date"])
assert len(with_data)==18
assert len(by_day)==12
assert sum(len(dates)==2 for dates in by_day.values())==6
assert sum(len(dates)==1 for dates in by_day.values())==6
assert max(len(dates) for dates in by_day.values())==2

again,repeat=batch.evaluate(config["records"],with_data,today)
assert not again and all(x["status"]=="unchanged" for x in repeat)

assert len(scoped)==4
assert not scope.check(scoped,with_data,projects,today)
assert {r["project_id"] for r in scoped}=={"the-9-stellars","celesta-gold","izumi-city","essensia-parkway"}
for pid in ("the-9-stellars","celesta-gold","izumi-city","essensia-parkway"):
    ref=next(x for x in scoped if x["project_id"]==pid)
    assert ref["asking_price_low_vnd_per_m2"]>0
    assert next(x for x in with_data if x["project_id"]==pid)["asking_price_low_vnd_per_m2"] is None

bad_scope=copy.deepcopy(scoped)
bad_scope[0]["asking_price_low_vnd_per_m2"]=123
assert any("price" in x for x in scope.check(bad_scope,with_data,projects,today))
bad_scope=copy.deepcopy(scoped)
bad_scope[0]["price_scope"]="mixed-residential"
assert scope.check(bad_scope,with_data,projects,today)

history_cfg=json.loads((ROOT/"config/history-coverage.json").read_text())
h=report.listing_report(history_cfg,with_data)
assert h["series_count"]==12 and h["trend_ready_series"]==0
assert h["minimum_span_days"]==30
assert sum(x["snapshot_count"]==2 for x in h["items"])==6
fake=[copy.deepcopy(new[0]) for _ in range(3)]
for r,day in zip(fake,("2026-10-09","2026-10-10","2026-10-11")):
    r["observation_date"]=day
assert report.listing_report(history_cfg,fake)["trend_ready_series"]==0, "Three adjacent days are NOT a price trend"
third=[copy.deepcopy(new[0]) for _ in range(3)]
for r,day in zip(third,("2026-09-01","2026-09-17","2026-10-09")):
    r["observation_date"]=day
assert report.listing_report(history_cfg,third)["trend_ready_series"]==1
third[-1]["asking_price_low_vnd_per_m2"]=None
assert report.listing_report(history_cfg,third)["trend_ready_series"]==0

print("Market listing coverage: 2 reviewed priced records + 4 non-chartable scoped references; 6/12 projects have two snapshots.")
