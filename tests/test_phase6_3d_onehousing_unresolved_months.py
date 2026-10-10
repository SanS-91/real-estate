"""Phase 6.3D — verified monthly publisher data is not a perpetual new candidate."""
from datetime import date
from pathlib import Path
import json,sys,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import market_alternative_auto_probe as probe
import market_source_reliability as rel

ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((ROOT/p).read_text(encoding="utf-8"))
cfg=read("config/market-alternative-auto-targets.json")
sources=read("data/mock/market/alternative-price-evidence.json")["data"] + read("data/mock/market/alternative-subproject-monthly-evidence.json")["data"]
refs={r["id"]:r for r in sources}
sub=read("data/mock/market/alternative-subproject-monthly-history.json")["data"]
parent=read("data/mock/market/onehousing-project-monthly-history.json")["data"]
published=sub+parent
target=next(t for t in cfg["targets"] if t["target_id"]=="onehousing-lumiere-boulevard-apartment")
baseline=refs[target["baseline_id"]]
latest=probe.latest_published_month(baseline,published)
assert latest and latest["period"]>baseline["period"]
assert latest["subproject_id"]==baseline["subproject_id"]=="lumiere-boulevard"
assert latest["review_status"]=="automated-source-verified"

def html(name,period,value,low,high):
    m,y=period.split("-")
    return (f"<html><body><h1>Căn hộ chung cư dự án {name} tháng {int(m)}/{y}</h1>"
            "Biến động giá & giá nhà chung cư theo tháng. Dữ liệu nguồn chính thức. "
            "Đơn giá phổ biến Mức giá/ mét vuông xuất hiện nhiều nhất trong khoảng giá "
            f"{value} triệu/m² 0% Khoảng giá: {low} - {high} triệu "
            "Giá thuê phổ biến ~20 triệu/tháng.</body></html>")
def page(row):
    year,month=row["period"].split("-")
    return html(row.get("subproject_name") or "Vinhomes Grand Park",
                month+"-"+year,
                str(row["value_vnd_per_m2"]/1e6),
                str(row["range_low_vnd_per_m2"]/1e6),
                str(row["range_high_vnd_per_m2"]/1e6))

today=date(2026,11,10)
status,price=probe.classify(target,page(latest),baseline,today,latest)
assert (status,price)==("published-period-unchanged",None),(status,price)
old=probe.classify(target,page(baseline),baseline,today,latest)
assert old==("older-period-no-candidate",None),old
conflict={**latest,"value_vnd_per_m2":latest["value_vnd_per_m2"]+1_000_000}
assert probe.classify(target,page(conflict),baseline,today,latest)==(
    "published-period-price-conflict",None)

future=html("Lumière Boulevard","11-2026","75.00","58.00","102.00")
status,candidate=probe.classify(target,future,baseline,today,latest)
assert status=="new-period-review-required" and candidate["period"]=="2026-11"
assert candidate["baseline_record_id"]==baseline["id"]
assert candidate["subproject_id"]=="lumiere-boulevard"
assert candidate["candidate_only"] is True and candidate["review_required"] is True
assert candidate["review_date"] is None
assert candidate["value_vnd_per_m2"]==75_000_000

# Never combine parent Vinhomes Grand Park and subproject Lumière Boulevard.
parent_target=next(t for t in cfg["targets"] if t["target_id"]=="onehousing-vinhomes-grand-park-apartment")
parent_base=refs[parent_target["baseline_id"]]
parent_latest=probe.latest_published_month(parent_base,published)
assert parent_latest and parent_latest.get("subproject_name") is None
assert parent_latest["project_id"]==baseline["project_id"]
assert probe.latest_published_month(parent_base,sub) is None
assert probe.latest_published_month(baseline,parent) is None
assert probe.latest_published_month(baseline,[{**latest,"subproject_id":"masteri-centre-point"}]) is None
assert probe.latest_published_month(baseline,[{**latest,"review_status":"candidate-only"}]) is None

# When a future month is published, October is not repeatedly collected.
def fetch(item,session):
    if item["target_id"]==target["target_id"]:
        return {"status":"reachable","http_status":200},page(latest)
    return {"status":"blocked","http_status":403},None
checks,candidates=probe.run([target],refs,today,None,fetcher=fetch,published_history=published)
assert len(checks)==1 and checks[0]["status"]=="published-period-unchanged"
assert checks[0]["latest_published_period"]==latest["period"]
assert candidates==[]

# Existing immutable candidate retains its original evidence for audit,
# while its published matching version no longer counts as pending work.
ledger=read("data/candidate/market/alternative-price-review-queue.json")
backlog=probe.candidate_backlog(ledger,published)
assert ledger["record_count"]==len(ledger["data"])
assert backlog["published_matched_count"]>=1 and backlog["pending_count"]==0,backlog
assert all(cid not in backlog["pending_ids"] for cid in backlog["published_matched_ids"])
mispriced=copy.deepcopy(ledger)
mispriced["data"][0]["value_vnd_per_m2"]+=5_000_000
conflicts=probe.candidate_backlog(mispriced,published)
assert conflicts["published_conflict_count"]==1 and conflicts["pending_count"]==1,conflicts
unknown=copy.deepcopy(ledger)
unknown["data"][0]["period"]="2026-11"
unresolved=probe.candidate_backlog(unknown,published)
assert unresolved["pending_count"]==1 and unresolved["published_matched_count"]==0
assert "published-period-unchanged" in rel.VALID_MONTHLY
print("PASS 6.3D: verified October is no longer an unresolved candidate, publisher scope is immutable, later months still queued")
