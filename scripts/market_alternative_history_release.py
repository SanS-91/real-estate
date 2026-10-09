"""Guarded release of reviewed OneHousing monthly category asking-price history.

Discovery is candidate-only. A separately committed approval is required.
Never add Rever single ads, CafeLand units, or Batdongsan portal ranges into
this publisher- and product-specific series.
"""
from __future__ import annotations
import argparse
import calendar
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/mock/market/alternative-monthly-history.json"
QUEUE = ROOT / "data/candidate/market/alternative-price-review-queue.json"
APPROVALS = ROOT / "config/market-alternative-reviewed-approvals.json"
REPORT = ROOT / "data/candidate/market/alternative-history-release-report.json"

SERIES_KEY = "onehousing-vinhomes-grand-park-apartment-popular-asking"
BASELINE_ID = "onehousing-vinhomes-grand-park-apartment-2026-10"
EXPECTED_URL = "https://onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Vinhomes-Grand-Park.1012"
METRIC_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*triệu\s*/?\s*m[²2]", re.I)
RANGE_RE = re.compile(r"Khoảng giá\s*[:|]?\s*(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*triệu", re.I)
MONTH_RE = re.compile(r"\btháng\s*(\d{1,2})\s*/\s*(20\d{2})\b", re.I)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def vnd(value):
    return int(round(float(value.replace(",", ".")) * 1_000_000))


def month_valid(period):
    if not isinstance(period, str) or not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", period):
        return False
    return True


def eligible_monthly(row):
    return (row.get("source_id") == "onehousing-vn"
            and row.get("project_id") == "vinhomes-grand-park"
            and row.get("asset_type") == "apartment"
            and row.get("metric_type") == "popular-asking-price-per-sqm"
            and row.get("period_type") == "month"
            and row.get("source_url") == EXPECTED_URL
            and row.get("range_low_vnd_per_m2") is not None
            and row.get("range_high_vnd_per_m2") is not None
            and month_valid(row.get("period")))


def quoted_metrics_match(row):
    e = row.get("evidence") or {}
    m, r, d = (METRIC_RE.search(str(e.get("metric") or "")),
               RANGE_RE.search(str(e.get("range") or "")),
               MONTH_RE.search(str(e.get("period") or "")))
    if not (m and r and d):
        return False
    lo, hi, val = vnd(r.group(1)), vnd(r.group(2)), vnd(m.group(1))
    period = f"{d.group(2)}-{int(d.group(1)):02d}"
    return (period == row.get("period")
            and (val,lo,hi) == (row.get("value_vnd_per_m2"),
                                row.get("range_low_vnd_per_m2"),
                                row.get("range_high_vnd_per_m2"))
            and 0 < lo <= val <= hi <= 1_000_000_000)


def base_issues(history):
    problems = []
    if not isinstance(history, list) or not history:
        return ["missing-monthly-baseline"]
    unique = set()
    latest = ""
    for row in history:
        period = row.get("period")
        if not eligible_monthly(row) or not quoted_metrics_match(row):
            problems.append("invalid-history-source-or-evidence")
        if period in unique:
            problems.append("duplicate-history-period")
        unique.add(period)
        if period and latest and period < latest:
            problems.append("out-of-order-history")
        if period:
            latest = period
        if row.get("series_key") != SERIES_KEY or row.get("review_status") not in ("reviewed-baseline","reviewed-release"):
            problems.append("missing-independent-reviewed-status")
        if not row.get("review_date"):
            problems.append("history-missing-review-date")
    if history[0].get("source_record_id") != BASELINE_ID or history[0].get("period") != "2026-10":
        problems.append("monthly-sequence-must-begin-from-reviewed-october-baseline")
    return problems


def evaluate(history, queue, approvals, today):
    """Return eligible additional periods and per-approval decisions; fail closed."""
    problems = base_issues(history)
    decisions, additional = [], []
    queue_by_id = {row.get("id"):row for row in queue}
    existing_period = {row["period"]:row for row in history}
    planned_period = set()
    seen_approvals = set()
    latest = max(existing_period) if existing_period else ""
    for approval in approvals:
        ident = approval.get("candidate_id")
        issues = []
        if not ident or ident in seen_approvals:
            issues.append("missing-or-duplicate-approval-id")
        seen_approvals.add(ident)
        candidate = queue_by_id.get(ident)
        if candidate is None:
            issues.append("candidate-not-in-immutable-review-queue")
        if approval.get("checked_source_evidence") is not True:
            issues.append("publisher-evidence-not-approved")
        if not isinstance(approval.get("review_note"), str) or len(approval["review_note"].strip()) < 20:
            issues.append("insufficient-review-note")
        try:
            reviewed = date.fromisoformat(approval.get("review_date",""))
            if reviewed > today:
                issues.append("approval-from-future")
        except ValueError:
            issues.append("invalid-review-date")
            reviewed = None
        if candidate:
            if not eligible_monthly(candidate) or not quoted_metrics_match(candidate):
                issues.append("candidate-source-price-scope-mismatch")
            if candidate.get("candidate_only") is not True or candidate.get("review_required") is not True:
                issues.append("candidate-not-review-pending")
            if candidate.get("baseline_record_id") != BASELINE_ID:
                issues.append("candidate-does-not-belong-to-original-series")
            if candidate.get("review_date") is not None:
                issues.append("candidate-already-has-review-date")
            period = candidate.get("period","")
            if period in planned_period:
                issues.append("duplicate-approval-period")
            planned_period.add(period)
            if reviewed and period > reviewed.strftime("%Y-%m"):
                issues.append("publisher-period-after-review-date")
            if period in existing_period:
                if (candidate.get("value_vnd_per_m2"),candidate.get("range_low_vnd_per_m2"),
                        candidate.get("range_high_vnd_per_m2")) != tuple(
                            existing_period[period].get(key) for key in
                            ("value_vnd_per_m2","range_low_vnd_per_m2","range_high_vnd_per_m2")):
                    issues.append("conflicting-existing-period")
                else:
                    decisions.append({"candidate_id":ident,"status":"already-published","issues":[]})
                    continue
            if period <= latest:
                issues.append("not-a-new-publisher-period")
            if not issues:
                row = {key: candidate[key] for key in (
                    "id","project_id","source_id","source_url","asset_type","metric_type",
                    "period","period_type","value_vnd_per_m2",
                    "range_low_vnd_per_m2","range_high_vnd_per_m2","evidence",
                    "methodology_note","source_publication_date")}
                row.update(series_key=SERIES_KEY, source_record_id=BASELINE_ID,
                           review_date=approval["review_date"], review_status="reviewed-release",
                           review_note=approval["review_note"])
                additional.append(row)
                latest = period
        decisions.append({"candidate_id":ident,"status":"blocked" if issues else "ready","issues":issues})
    return additional, decisions, problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preview","promote"), default="preview")
    parser.add_argument("--today", default=date.today().isoformat())
    args = parser.parse_args()
    today = date.fromisoformat(args.today)
    history = load(BASE)
    q = load(QUEUE)
    a = load(APPROVALS)
    if q.get("record_count") != len(q.get("data",[])) or a.get("record_count") != len(a.get("data",[])):
        raise SystemExit("Queue or approval registry record_count mismatch")
    rows, decisions, problems = evaluate(history["data"],q["data"],a["data"],today)
    report = {"mode":args.mode,"checked_date":str(today),"existing_monthly_records":len(history["data"]),
              "approvals_checked":len(a["data"]),"ready_for_promotion":len(rows),
              "blocked":sum(d["status"]=="blocked" for d in decisions),
              "conflicts":problems,"decisions":decisions,
              "production_updated":bool(args.mode=="promote" and rows and not problems)}
    save(REPORT, report)
    if problems or report["blocked"]:
        raise SystemExit("Source/approval gate blocked: " + json.dumps(report,ensure_ascii=False))
    if args.mode=="promote" and rows:
        history["data"].extend(rows)
        history["record_count"]=len(history["data"])
        save(BASE,history)
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
