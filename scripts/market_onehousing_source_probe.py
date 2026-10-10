"""Read-only OneHousing monthly source health: exact-project publisher URLs only.

Never stores page HTML, prices, review candidates or publication changes.
Run on GitHub-hosted PR and production safely for Masteri diagnostics.
"""
import json
from datetime import date
from pathlib import Path
import requests
import market_alternative_auto_probe as probe

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/market-alternative-auto-targets.json"
BASE=ROOT/"data/mock/market/alternative-subproject-monthly-evidence.json"
HISTORY=ROOT/"data/mock/market/alternative-subproject-monthly-history.json"
TARGET_ID="onehousing-masteri-centre-point-apartment"

def inspect(fetcher=probe.fetch_with_publisher_fallback, now=None):
    now=now or date.today()
    cfg=probe.load(CONFIG)["targets"]
    target=next(x for x in cfg if x["target_id"]==TARGET_ID)
    baseline=next(x for x in probe.load(BASE)["data"] if x["id"]==target["baseline_id"])
    published=probe.load(HISTORY)["data"]
    latest=probe.latest_published_month(baseline,published)
    access,html=fetcher(target,requests.Session())
    if html is None:
        status=access.get("status","source-unavailable")
    else:
        status,_=probe.classify(target,html,baseline,now,latest)
    return {
        "target_id":TARGET_ID,
        "source_checks_only":True,
        "production_written":False,
        "candidate_written":False,
        "reviewed_baseline_period":baseline["period"],
        "latest_published_period":(latest or baseline)["period"],
        "source_status":status,
        "source_variants":access.get("source_variants",[]),
        "methodology":"Official exact-ID publisher HTML only; indexed cached months do not create a live, verified price. Check 401/403/429 before attempting the pinned official mirror. No review, publish, backfill or source access bypass."
    }

def main():
    print(json.dumps(inspect(),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
