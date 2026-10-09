"""Source checks are only operational evidence, never historical price snapshots."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location("probe",ROOT/"scripts/market_secondary_listing_probe.py")
probe=importlib.util.module_from_spec(sp);sp.loader.exec_module(probe)
rows=json.loads((ROOT/"data/mock/market/secondary-listing-evidence.json").read_text(encoding="utf-8"))["data"]
assert len(rows)==3
for row in rows:
    ev=row["evidence"]
    html=f"""<html><body><h1>{ev['project']}</h1><p>{ev['listing']}</p>
      <p>{ev['date']}</p><p>Giá bán {ev['price']}</p>
      <p>{ev['area']}</p><p>{ev['total']}</p><p>Thông tin bất động sản chi tiết</p></body></html>"""
    response=probe.classify(row,html)
    assert response["status"]=="source-evidence-visible",response
    assert all(response["evidence_fields"].values())
    assert probe.classify(row,html.replace(row["listing_id"],"WRONG-LISTING"))["status"]=="reachable-review-required"
    assert probe.classify(row,html.replace(ev["price"],"No verified price"))["status"]=="reachable-review-required"
    assert probe.classify(row,"<html>Captcha - checking your browser</html>")["status"]=="blocked-or-empty-page"

def fake_fetch(row,session):
    return {"status":"blocked","http_status":403}
checked=probe.probe(rows,None,fetcher=fake_fetch)
assert len(checked)==3
assert all(x["status"]=="blocked" for x in checked)
assert all("observation_date" not in x and "value_vnd_per_m2" not in x for x in checked)
print("PASS: 3 publisher source checks, price/area/date evidence verification; blocked/missing sources never mint history.")
