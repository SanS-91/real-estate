#!/usr/bin/env python3
"""Keep the official 2025-26 monthly CPI history exact and live Macro immutable."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data/processed/macro/historical-observations.json"
CURRENT = ROOT / "data/processed/macro/observations.json"

# One value per *monthly* observation. Do not substitute averages or
# year-to-date changes for the particular month.
EXPECTED = {
    "2025": {
        "cpi-yoy": [3.63, 2.91, 3.13, 3.12, 3.24, 3.57, 3.19, 3.24, 3.38, 3.25, 3.58, 3.48],
        "cpi-mom": [0.98, 0.34, -0.03, 0.07, 0.16, 0.48, 0.11, 0.05, 0.42, 0.20, 0.45, 0.19],
        "core-cpi-yoy": [3.07, 2.87, 3.10, 3.14, 3.33, 3.46, 3.30, 3.25, 3.18, 3.30, 3.28, 3.27],
    },
    "2026": {
        "cpi-yoy": [2.53, 3.35, 4.65, 5.46, 5.60, 4.69, 4.45, 4.89],
        "cpi-mom": [0.05, 1.14, 1.23, 0.84, 0.29, -0.39, -0.12, 0.47],
        "core-cpi-yoy": [3.19, 3.74, 3.96, 4.66, 4.67, 4.50, None, None],
    },
}
VALID_IDS = set(EXPECTED["2025"])
PERIOD_URL_PART = {
    "2025-01": "thang-mot-nam-2025",
    "2025-02": "thang-hai-va-02-thang-nam-2025",
    "2025-03": "thang-ba-va-quy-i-nam-2025",
    "2025-04": "thang-tu-va-4-thang-dau-nam-2025",
    "2025-05": "thang-nam-va-5-thang-dau-nam-2025",
    "2025-06": "thang-sau-quy-ii-va-6-thang-dau-nam-2025",
    "2025-07": "thang-bay-va-7-thang-nam-2025",
    "2025-08": "thang-tam-va-8-thang-nam-2025",
    "2025-09": "thang-chin-quy-iii-va-9-thang-nam-2025",
    "2025-10": "thang-muoi-va-10-thang-nam-2025",
    "2025-11": "thang-muoi-mot-va-11-thang-nam-2025",
    "2025-12": "thang-muoi-hai-quy-iv-va-nam-2025",
}

def validate():
    payload = json.loads(HISTORY.read_text(encoding="utf-8"))
    live = json.loads(CURRENT.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["mode"] == "verified-official-nso-history-v1"
    assert payload["repository_publish"] is True and payload["frontend_publish"] is False
    assert payload["record_count"] == len(payload["data"]) == 58
    assert live["record_count"] == len(live["data"])
    assert payload["coverage"]["first_period"] == "2025-01"
    assert payload["coverage"]["last_period"] == "2026-08"
    assert payload["coverage"]["years"]["2025"]["record_count"] == 36

    live_keys = {(r["indicator_id"], r["period_type"], r["period"]) for r in live["data"]}
    seen = set()
    by_year = {"2025": 0, "2026": 0}
    for row in payload["data"]:
        key = (row.get("indicator_id"), row.get("period_type"), row.get("period"))
        assert key not in seen, ("duplicate historical record", key)
        assert key not in live_keys, ("historical data would overwrite live production", key)
        seen.add(key)
        year = row["period"][:4]
        month = int(row["period"][-2:])
        assert year in EXPECTED
        assert row["indicator_id"] in VALID_IDS
        assert row["period_type"] == "month" and re.fullmatch(r"202[56]-(0[1-9]|1[0-2])", row["period"])
        assert row["unit"] == "percent"
        assert row["source_id"] == "nso-vietnam"
        source = urlparse(row["source_url"])
        assert source.scheme == "https" and source.hostname == "www.nso.gov.vn"
        assert row["evidence_status"] == "verified" and row["observation_status"] == "final"
        assert row["historical_observation"] is True and row["source_reviewed_at"]
        assert row["published_at"] > row["period"] and row["fetched_at"]
        assert row["source_record_id"] == row["id"] == f"nso-historical-{row['indicator_id']}-{row['period']}"
        assert row["value"] == EXPECTED[year][row["indicator_id"]][month - 1]
        if year == "2025":
            assert PERIOD_URL_PART[row["period"]] in row["source_url"]
            assert row["published_at"] > row["period"] + "-01"
        by_year[year] += 1

    assert by_year == {"2025": 36, "2026": 22}
    for year, groups in EXPECTED.items():
        for indicator, values in groups.items():
            count = sum(value is not None for value in values)
            assert sum(row["indicator_id"] == indicator and row["period"].startswith(year)
                       for row in payload["data"]) == count

    js = (ROOT / "assets/js/macro.js").read_text(encoding="utf-8")
    store = (ROOT / "assets/js/data-store.js").read_text(encoding="utf-8")
    html = (ROOT / "macro.html").read_text(encoding="utf-8")
    assert "getVerifiedMacroHistory" in store and "getVerifiedMacroHistory" in js
    assert "validHistoricalRows" in js and "currentProductionRows" in js
    assert "historical-observations.json" in store
    assert 'assets/js/macro.js?v=4.9I1' in html
    assert re.search(r'history=20261012H[0-9]+', html), "Macro must include cache-busting history revision"
    assert "historicalCount" in js
    return {"historical_records": len(seen), "2025": by_year["2025"],
            "2026": by_year["2026"], "live_protected": len(live_keys)}

if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
