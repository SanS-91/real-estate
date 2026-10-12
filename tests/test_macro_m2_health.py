from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_data_health import latest_due_quarter, m2_release_observation, row_status, prod_info


def asof(date_str):
    return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)


def main():
    history=json.loads((ROOT/"data/processed/macro/historical-monetary-observations.json").read_text())
    live=json.loads((ROOT/"data/processed/macro/observations.json").read_text())
    past=history["data"]; current=live["data"]

    assert latest_due_quarter(asof("2026-10-12T08:00:00"))=="2026-06"
    assert latest_due_quarter(asof("2026-10-16T08:00:00"))=="2026-09"

    status=m2_release_observation(asof("2026-10-12T08:00:00"),current,past)
    assert status["release_expected_period"]=="2026-06"
    assert status["release_latest_period"]=="2026-03"
    assert status["release_status"]=="missing-release"
    assert status["source_freshness"]=="release-missing"

    fake_success=[{"indicator_id":"m2-growth-ytd","period":"2026-09","period_type":"month",
        "source_id":"nso-vietnam","evidence_status":"verified","observation_status":"final",
        "comparison_base":"previous-year-end","value":6.8}]
    # A source-reviewed new quarter clears the release gap without mutation of history.
    recovered=m2_release_observation(asof("2026-10-16T08:00:00"),fake_success,past)
    assert recovered["release_status"]=="current"
    assert recovered["release_latest_period"]=="2026-09"

    # An unapproved YoY or DEMO value cannot silence the missing-release alert.
    counterfeit={**fake_success[0],"comparison_base":"year-on-year"}
    missing=m2_release_observation(asof("2026-10-16T08:00:00"),[counterfeit],past)
    assert missing["release_status"]=="missing-release"

    config=json.loads((ROOT/"config/operations_health.json").read_text())
    matrix=json.loads((ROOT/"config/update_matrix.json").read_text())
    target=next(x for x in config["datasets"] if x["id"]=="macro-m2-ytd")
    m={x["id"]:x for x in matrix["datasets"]}
    prod=prod_info(target,m,asof("2026-10-12T08:00:00"))
    assert prod["release_status"]=="missing-release",prod
    assert prod["record_count"]==0,prod
    assert row_status(prod,{"candidate_backlog":0,"candidate_conflicts":0},
                      {"workflow_status":"healthy"})=="review"
    assert m["macro-m2-ytd"]["indicator_ids"]==["m2-growth-ytd"]
    print("PASS M2 overdue quarter release monitoring, no false Healthy and no YoY substitution")


if __name__=="__main__":
    main()
