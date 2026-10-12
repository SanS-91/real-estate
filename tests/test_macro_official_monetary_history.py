"""Regression: official NSO M2/credit/funding YTD, official SBV rate ranges."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
HISTORY=ROOT/"data/processed/macro/historical-monetary-observations.json"
CURRENT=ROOT/"data/processed/macro/observations.json"
CPI=ROOT/"data/processed/macro/historical-observations.json"

# [M2 YTD, capital mobilization YTD, credit YTD] from NSO quarterly reports.
QUARTERS={
"2024-09":("2024-09-27",[5.10,4.79,8.53]),
"2024-12":("2024-12-25",[9.42,9.06,13.82]),
"2025-03":("2025-03-25",[1.99,1.36,2.49]),
"2025-06":("2025-06-26",[7.09,6.11,8.30]),
"2025-09":("2025-09-25",[10.61,9.74,13.00]),
"2025-12":("2025-12-22",[14.98,13.68,17.65]),
"2026-03":("2026-03-24",[1.04,0.44,2.15]),
}
IDS=["m2-growth-ytd","bank-funding-growth-ytd","credit-growth-ytd"]
RATE={
"2025-06":[4.5,5.5,6.5,8.8],
"2025-07":[4.6,5.5,6.5,8.9],
}
RATE_IDS=["deposit-rate-vnd-6-12m-low","deposit-rate-vnd-6-12m-high",
"lending-rate-vnd-average-low","lending-rate-vnd-average-high"]

def main():
    history=json.loads(HISTORY.read_text(encoding="utf-8"))
    live=json.loads(CURRENT.read_text(encoding="utf-8"))
    cpi=json.loads(CPI.read_text(encoding="utf-8"))
    assert history["mode"]=="official-monetary-history-v1"
    assert history["record_count"]==len(history["data"])==29
    assert history["repository_publish"] is True
    assert history["frontend_publish"] is False
    canonical_keys={(r["indicator_id"],r["period_type"],r["period"]) for r in live["data"]+cpi["data"]}
    seen=set()
    for row in history["data"]:
        key=(row["indicator_id"],row["period_type"],row["period"])
        assert key not in canonical_keys, ("historical-canonical overlap",key)
        assert key not in seen, ("duplicate historical key",key)
        seen.add(key)
        assert row["observation_status"]=="final" and row["evidence_status"]=="verified"
        assert row["historical_observation"] is True
        assert row["period_type"]=="month" and row["source_release_period"]
        assert row["unit"] in ("percent","percent-per-year")
        assert row["source_record_id"]==row["id"]
        assert row["published_at"] is None, "unknown publication day must not be fabricated"
        host=urlparse(row["source_url"]).hostname
        assert host in ["www.nso.gov.vn","www.sbv.gov.vn","sbv.gov.vn"]
        if row["indicator_id"] in IDS:
            i=IDS.index(row["indicator_id"]);period=row["period"]
            assert period in QUARTERS
            assert row["source_id"]=="nso-vietnam"
            assert row["value"]==QUARTERS[period][1][i],row
            assert row["as_of_date"]==row["data_date"]==QUARTERS[period][0]
            assert row["comparison_base"]=="previous-year-end"
            assert row["reporting_cadence"]=="quarterly"
            assert row["unit"]=="percent"
        else:
            i=RATE_IDS.index(row["indicator_id"]); period=row["period"]
            assert period in RATE and row["source_id"]=="sbv-vietnam"
            assert row["value"]==RATE[period][i]
            assert row["rate_bound"]==("low" if i%2==0 else "high")
            assert row["unit"]=="percent-per-year"
            assert ".pdf" in row["source_url"].lower()
    for period in QUARTERS:
        assert len([x for x in history["data"] if x["period"]==period and x["indicator_id"] in IDS])==3
    for period in RATE:
        assert len([x for x in history["data"] if x["period"]==period and x["indicator_id"] in RATE_IDS])==4
    macro=(ROOT/"assets/js/macro.js").read_text(encoding="utf-8")
    assert "getVerifiedMonetaryHistory" in macro
    assert "validOfficialMonetaryRows" in macro
    assert "New YTD baseline" in macro
    indicator=json.loads((ROOT/"data/mock/macro/indicators.json").read_text(encoding="utf-8"))
    assert any(x["id"]=="m2-growth-ytd" for x in indicator["data"])
    assert (ROOT/"assets/js/data-store.js").read_text().count("getVerifiedMonetaryHistory")==1
    print("PASS monetary history: 21 NSO quarterly + 8 SBV monthly low/high, sources & baselines")

if __name__=="__main__":
    main()
