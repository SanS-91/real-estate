"""Alternative-source probe regression: no synthetic periods, unsafe merges or promotion."""
from __future__ import annotations
import copy
import importlib.util
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "auto_probe", ROOT / "scripts/market_alternative_auto_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
cfg = json.loads((ROOT / "config/market-alternative-auto-targets.json").read_text(encoding="utf-8"))
refs = (json.loads((ROOT / "data/mock/market/alternative-price-evidence.json").read_text(encoding="utf-8"))["data"]
        + json.loads((ROOT / "data/mock/market/alternative-subproject-monthly-evidence.json").read_text(encoding="utf-8"))["data"])
by_id = {r["id"]: r for r in refs}
target = cfg["targets"][0]
prior = by_id[target["baseline_id"]]

def fixture(month=11, year=2026, amount="55.10", low="38.40", high="250.25"):
    return f"""<!doctype html><html><head><title>Vinhomes Grand Park - OneHousing</title></head><body>
        <main><h1>Căn hộ chung cư dự án Vinhomes Grand Park tháng {month}/{year}</h1>
        <section>Khoảng giá: 1.35 - 32 tỷ</section>
        <section>Đơn giá phổ biến
        Mức giá/ mét vuông xuất hiện nhiều nhất trong khoảng giá
        {amount} triệu/m² 0%</section>
        <section>Khoảng giá: {low} - {high} triệu</section>
        <section>Giá thuê phổ biến ~7.09 triệu/tháng</section>
        <p>Thống kê tin chào bán theo tháng tại dự án Vinhomes Grand Park
        Căn hộ chung cư đang được rao bán theo từng phân khúc sản phẩm.</p></main>
        </body></html>"""

def rever_fixture(day="17", amount="48.60"):
    return f"""<html><body><h1>Căn hộ Vinhomes Grand Park</h1><p>69m²</p>
    <p>Giá tham khảo {amount} triệu/m²</p><p>Cập nhật: {day}/09/2026</p>
    <p>Chi tiết căn hộ và mức giá tham khảo tại trang tin Rever.</p></body></html>"""

now = date(2026, 11, 9)
assert len(cfg["targets"]) == 6
assert {x["mode"] for x in cfg["targets"]} == {
    "monthly-price-candidate", "single-listing-review", "historical-reference-monitor"}
assert all(probe.allowed_target(x) for x in cfg["targets"])
assert not probe.allowed_target(dict(target,url="http://127.0.0.1/local"))
assert not probe.allowed_target(dict(target,url="https://not-onehousing.vn/price"))
assert not probe.allowed_target(dict(target,url=target["url"]+"?q=force"))
assert probe.plain_text('<p>One <b>Two</b></p><script>fake</script>') == 'One Two'

parsed = probe.onehousing_monthly(probe.plain_text(fixture()), now)
assert parsed["period"] == "2026-11"
assert parsed["value_vnd_per_m2"] == 55_100_000
assert parsed["range_low_vnd_per_m2"] == 38_400_000
assert parsed["range_high_vnd_per_m2"] == 250_250_000
assert probe.onehousing_monthly(probe.plain_text(fixture(month=12)), now) is None
archived = probe.onehousing_monthly(probe.plain_text(fixture(month=8,amount="57.24",low="38.55",high="331.19")), now)
assert archived["period"] == "2026-08" and archived["value_vnd_per_m2"] == 57_240_000
assert probe.classify(target,fixture(month=8,amount="57.24",low="38.55",high="331.19"),prior,now) == ("older-period-no-candidate",None)
assert probe.onehousing_monthly(probe.plain_text(fixture(low="90")), now) is None
assert probe.onehousing_monthly(probe.plain_text(fixture().replace("Vinhomes Grand Park", "Izumi City")), now) is None
assert probe.normal_name("Lumière Boulevard") == probe.normal_name("Lumiere   Boulevard")
for candidate_name in ("Lumière Boulevard", "Masteri Centre Point"):
    sample = probe.plain_text(fixture().replace("Vinhomes Grand Park", candidate_name))
    assert probe.onehousing_monthly(sample, now, candidate_name)["period"] == "2026-11"
    assert probe.onehousing_monthly(sample, now, "Vinhomes Grand Park") is None
for row in cfg["targets"][4:]:
    assert probe.publisher_hosts(row["source_id"])
    actual = by_id[row["baseline_id"]]
    assert actual["subproject_name"] == row["publisher_project_name"]
    assert actual["project_id"] == "vinhomes-grand-park"
    assert row["mode"] == "monthly-price-candidate"
    same_month = fixture(month=9,amount=str(actual["value_vnd_per_m2"]/1000000),
           low=str(actual["range_low_vnd_per_m2"]/1000000),
           high=str(actual["range_high_vnd_per_m2"]/1000000)).replace("Vinhomes Grand Park",row["publisher_project_name"])
    assert probe.classify(row,same_month,actual,date(2026,10,9)) == ("same-period-unchanged",None)

assert probe.onehousing_monthly("Đơn giá phổ biến 100 triệu/m² Khoảng giá 90 - 110 triệu", now) is None
assert probe.classify(target, fixture(month=10, amount="54.47", low="36.81", high="331.19"), prior, now) == ("same-period-unchanged",None)

status, new = probe.classify(target, fixture(), prior, now)
assert status == "new-period-review-required" and new
assert new["period"] == "2026-11" and new["id"].endswith("2026-11")
assert new["candidate_only"] and new["review_required"] and new["review_date"] is None
assert new["source_id"] == "onehousing-vn" and new["metric_type"] == "popular-asking-price-per-sqm"
assert "asking_price_low_vnd_per_m2" not in new and "average_asp" not in new
assert probe.classify(target, fixture(month=10,amount="60"), prior,now) == ("same-period-review-required",None)
assert probe.classify(target,fixture(month=9),prior,now) == ("older-period-no-candidate",None)
assert probe.classify(target,"<html><body>captcha</body></html>",prior,now) == ("blocked-or-empty-page",None)

single_target=cfg["targets"][1]
single_prior=by_id[single_target["baseline_id"]]
rev=probe.rever_single_listing(probe.plain_text(rever_fixture()),date(2026,10,9))
assert rev["period"]=="2026-09-17" and rev["value_vnd_per_m2"]==48_600_000
assert probe.rever_single_listing(probe.plain_text(rever_fixture(day="31")),date(2026,10,9)) is None
assert probe.classify(single_target,rever_fixture(),single_prior,date(2026,10,9))[0]=="new-period-review-required"
assert probe.classify(single_target,rever_fixture(day="16",amount="48.55"),single_prior,date(2026,10,9)) == ("same-period-unchanged",None)

for historic in cfg["targets"][2:4]:
    status,candidate=probe.classify(historic,fixture(),by_id[historic["baseline_id"]],now)
    assert status=="reachable-historical-reference-frozen" and candidate is None

def fake_fetch(item, session):
    if item["mode"] == "monthly-price-candidate":
        name=item.get("publisher_project_name", "Vinhomes Grand Park")
        html=fixture(month=11).replace("Vinhomes Grand Park",name)
        return {"status":"reachable","http_status":200}, html
    if item["mode"] == "single-listing-review":
        return {"status":"blocked","http_status":403}, None
    return {"status":"reachable","http_status":200}, fixture()
checks,candidates=probe.run(cfg["targets"],by_id,now,None,fetcher=fake_fetch)
assert len(checks)==6 and len(candidates)==3
assert sum(row["status"]=="new-period-review-required" for row in checks)==3
assert sum(row["status"]=="blocked" for row in checks)==1
assert all(not x.get("production_written",False) for x in checks)
queue={"schema_version":1,"candidate_only":True,"review_required":True,"data":[]}
added,conflicts=probe.append_review_queue(queue,candidates)
assert (added,conflicts,queue["record_count"])==(3,0,3)
added,conflicts=probe.append_review_queue(queue,candidates)
assert (added,conflicts,queue["record_count"])==(0,0,3)
tampered=copy.deepcopy(candidates[0])
tampered["value_vnd_per_m2"]=111_000_000
added,conflicts=probe.append_review_queue(queue,[tampered])
assert (added,conflicts,queue["record_count"])==(0,1,3)
assert queue["data"][0]["value_vnd_per_m2"]==55_100_000
assert json.loads((ROOT/"data/candidate/market/alternative-price-review-queue.json").read_text())["record_count"]==0
print("PASS: 6 source targets, 3 distinct OneHousing apartment series, strict name/month matching, and safe review queue.")
