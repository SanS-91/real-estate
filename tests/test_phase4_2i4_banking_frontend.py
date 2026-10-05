from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    processed = json.loads((ROOT / "data/processed/macro/observations.json").read_text(encoding="utf-8"))
    assert processed["repository_publish"] is True
    assert processed["record_count"] == 8
    rows = processed["data"]

    by_id = {}
    for row in rows:
        by_id.setdefault(row["indicator_id"], []).append(row)

    for iid, expected in (
        ("credit-growth-ytd", 10.89),
        ("bank-funding-growth-ytd", 9.78),
    ):
        assert iid in by_id
        assert len(by_id[iid]) == 1, f"{iid} should start with one controlled production observation"
        row = by_id[iid][0]
        assert row["value"] == expected
        assert row["source_id"] == "nso-vietnam"
        assert row["evidence_status"] == "verified"
        assert row["observation_status"] == "final"
        assert row["period"] == "2026-09"
        assert row["period_type"] == "month"

    js = (ROOT / "assets/js/macro.js").read_text(encoding="utf-8")
    assert "['credit-growth-ytd', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }]" in js
    assert "['bank-funding-growth-ytd', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }]" in js
    assert "liquidity: ['interbank-on', 'credit-growth-ytd', 'bank-funding-growth-ytd', 'm2-growth-yoy']" in js
    assert "'credit-growth-ytd','bank-funding-growth-ytd','cpi-yoy'" in js
    assert "Latest observation only · no synthetic history is created." in js
    assert "const retainedMockRows = mockRows.filter(row => !productionIndicatorIds.has(row.indicator_id));" in js

    # Production values must come from processed observations, not hard-coded frontend snapshots.
    assert "10.89" not in js
    assert "9.78" not in js

    mapping = json.loads((ROOT / "config/frontend_indicator_map.json").read_text(encoding="utf-8"))
    assert mapping["frontend_baseline"] in {"v7.2.1+4.2I4", "v7.2.1+4.2I5", "v7.2.1+4.2I5.1"}
    assert mapping["mappings"]["credit-growth-ytd"]["status"] == "compatible"
    assert mapping["mappings"]["bank-funding-growth-ytd"]["status"] == "compatible"

    html = (ROOT / "macro.html").read_text(encoding="utf-8")
    assert "macro.js?v=4.2I5.1" in html
    assert "localization-dynamic.js?v=4.2I5.1" in html
    assert "main.css?v=4.2I4" in html

    print("Phase 4.2I.4 banking frontend sync tests passed")


if __name__ == "__main__":
    main()
