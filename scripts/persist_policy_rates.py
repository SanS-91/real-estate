from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse, hashlib, json, os, tempfile

HERE = Path(__file__).resolve(); ROOT = HERE.parents[1]

def read_json(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def atomic_write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="policy-rates-persist-", dir=str(path.parent)))
    try:
        tmp = temp_root / path.name; write_json(tmp, payload); os.replace(tmp, path)
    finally:
        try: temp_root.rmdir()
        except OSError: pass
def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(65536), b""): h.update(chunk)
    return h.hexdigest()
def now_iso(): return datetime.now(timezone.utc).isoformat()
def logical_key(r, fields):
    vals=tuple(r.get(k) for k in fields)
    if any(v in (None,"") for v in vals): raise ValueError(f"Missing logical-key field for record {r.get('id')}: {fields}")
    return vals
def make_index(records, fields):
    out={}; ids=set()
    for r in records:
        rid=r.get("id")
        if not rid or rid in ids: raise ValueError(f"Missing/duplicate record id: {rid}")
        ids.add(rid); key=logical_key(r,fields)
        if key in out: raise ValueError(f"Duplicate logical key: {key}")
        out[key]=r
    return out
def parse_date(v: str) -> date:
    try: return datetime.strptime(v, "%Y-%m-%d").date()
    except Exception as exc: raise ValueError(f"Policy-rate auto-publish requires YYYY-MM-DD period; got {v!r}") from exc


def build_policy_rates_persistence(incoming_dir: Path, repo_processed_dir: Path, report_dir: Path, source_run_number: int, source_run_database_id: str, auto_policy_path: Path, gate_path: Path, as_of: datetime | None=None):
    policy=read_json(auto_policy_path); gate=read_json(gate_path)
    if policy.get("mode") != "controlled-policy-rates-auto-persistence-v1": raise ValueError("Safety violation: invalid policy-rate auto-persistence policy")
    if policy.get("repository_publish") is not True or policy.get("frontend_publish") is not False: raise ValueError("Safety violation: policy-rate policy must publish repository only")
    if gate.get("mode") != "controlled-production-v1" or gate.get("production_write") is not True: raise ValueError("Safety violation: invalid policy-rate production gate")
    incoming=read_json(incoming_dir/"observations.json"); run=read_json(incoming_dir/"promotion-run.json")
    rows=incoming.get("data",[])
    if incoming.get("record_count") != len(rows): raise ValueError("Incoming record_count mismatch")
    if incoming.get("production_write") is not True or incoming.get("repository_publish") is not False or incoming.get("frontend_publish") is not False: raise ValueError("Incoming file is not pre-persistence controlled production")
    if run.get("mode") != "controlled-production-v1" or run.get("conflict_count") != 0: raise ValueError("Incoming production run is not conflict-free controlled production")
    if run.get("final_record_count") != len(rows) or run.get("source_run_id") != incoming.get("source_run_id"): raise ValueError("Incoming production metadata mismatch")
    repo_obs=repo_processed_dir/"observations.json"; repo_meta=repo_processed_dir/"repository-publish.json"
    current=read_json(repo_obs); old_rows=current.get("data",[])
    if current.get("record_count") != len(old_rows) or current.get("repository_publish") is not True: raise ValueError("Repository observations are not canonical")
    fields=list(policy.get("logical_key_fields",["indicator_id","period_type","period"])); old_idx=make_index(old_rows,fields); new_idx=make_index(rows,fields)
    if policy.get("require_prior_count_match",True) and run.get("prior_record_count") != len(old_rows): raise ValueError(f"Stale baseline blocked: production prior_record_count={run.get('prior_record_count')}, repository count={len(old_rows)}")
    for key, old in old_idx.items():
        new=new_idx.get(key)
        if new is None: raise ValueError(f"Record-drop blocked: {key}")
        if new != old: raise ValueError(f"Historical mutation blocked: {key}")
    additions=[r for k,r in new_idx.items() if k not in old_idx]
    if not additions:
        report={"schema_version":1,"generated_at":now_iso(),"mode":policy["mode"],"status":"no-change","repository_write":False,"git_commit_expected":False,"source_run_number":source_run_number,"source_run_database_id":str(source_run_database_id),"prior_record_count":len(old_rows),"added_record_count":0,"final_record_count":len(old_rows),"notes":["No new fully corroborated SBV policy-rate event; repository remains unchanged."]}
        write_json(report_dir/"policy-rates-auto-persistence.json",report); return report
    allowed=set(policy.get("allowed_indicator_ids",[])); required=int(policy.get("required_bundle_size",len(allowed)))
    if len(additions) != required or {r.get("indicator_id") for r in additions} != allowed: raise ValueError("Safety stop: policy-rate auto-persistence requires one complete three-rate event")
    if len(additions) > int(policy.get("max_additions_per_run",3)): raise ValueError("Safety stop: policy-rate additions exceed configured maximum")
    periods={r.get("period") for r in additions}
    if len(periods) != 1: raise ValueError(f"Policy-rate bundle must use one common effective date; got {sorted(periods)}")
    event_period=next(iter(periods)); event_date=parse_date(event_period)
    local_now=as_of.astimezone(ZoneInfo(policy.get("timezone","Asia/Ho_Chi_Minh"))) if as_of else datetime.now(ZoneInfo(policy.get("timezone","Asia/Ho_Chi_Minh")))
    if (event_date-local_now.date()).days > int(policy.get("max_future_days",0)): raise ValueError(f"Future policy-rate event blocked: {event_period}")
    gate_allowed=gate.get("allowed_indicators",{}); required_sources=set(policy.get("required_corroboration_source_ids",[]))
    latest={}
    for r in old_rows:
        iid=r.get("indicator_id")
        if iid in allowed and r.get("period_type")=="date":
            p=r.get("period")
            if iid not in latest or p>latest[iid]: latest[iid]=p
    for r in additions:
        iid=r.get("indicator_id"); cfg=gate_allowed.get(iid)
        if not cfg: raise ValueError(f"Indicator not in policy-rate gate: {iid}")
        if r.get("period_type")!="date" or r.get("evidence_status")!="corroborated": raise ValueError(f"Policy-rate evidence/period mismatch for {iid}")
        if r.get("source_id") not in set(cfg.get("allowed_sources",[])): raise ValueError(f"Unapproved policy-rate source for {iid}: {r.get('source_id')}")
        if r.get("observation_status")!="final": raise ValueError(f"Non-final policy-rate record blocked: {r.get('id')}")
        if required_sources-set(r.get("corroboration_source_ids",[])): raise ValueError(f"Missing required corroboration sources for {iid}")
        if any(k.startswith("preview_") for k in r) or "preview_only" in r: raise ValueError(f"Preview-only field leaked into policy-rate record: {r.get('id')}")
        if latest.get(iid) and event_period <= latest[iid]: raise ValueError(f"Non-forward policy-rate event blocked for {iid}: {event_period} <= {latest[iid]}")
    old_meta=read_json(repo_meta) if repo_meta.exists() else {}; prior=old_meta.get("source_run_number")
    if policy.get("require_monotonic_source_run_number",True) and prior is not None and int(source_run_number)<=int(prior): raise ValueError(f"Source run number must advance beyond repository run #{prior}; got #{source_run_number}")
    published=now_iso(); output=deepcopy(incoming); output.update({"repository_publish":True,"frontend_publish":False,"repository_published_at":published,"repository_source_run_number":source_run_number,"repository_source_run_database_id":str(source_run_database_id),"repository_persistence_mode":policy["mode"]})
    meta={"schema_version":1,"generated_at":published,"mode":policy["mode"],"repository_publish":True,"frontend_publish":False,"source_workflow":policy.get("source_workflow"),"source_run_number":source_run_number,"source_run_database_id":str(source_run_database_id),"source_artifact":f"{policy.get('source_artifact_prefix','macro-production-')}{source_run_number}","source_promotion_run_id":incoming.get("source_run_id"),"source_generated_at":incoming.get("generated_at"),"prior_record_count":len(old_rows),"added_record_count":len(additions),"final_record_count":len(rows),"observations_sha256":None,"rollback":"Use git history/revert. Policy-rate automation is complete-event, append-only, and retain-last-good."}
    atomic_write_json(repo_obs,output); meta["observations_sha256"]=sha256(repo_obs); atomic_write_json(repo_meta,meta)
    report={"schema_version":1,"generated_at":published,"mode":policy["mode"],"status":"ready-to-commit","repository_write":True,"git_commit_expected":True,"source_run_number":source_run_number,"source_run_database_id":str(source_run_database_id),"prior_record_count":len(old_rows),"added_record_count":len(additions),"final_record_count":len(rows),"observations_sha256":meta["observations_sha256"],"period":event_period,"added":[{"indicator_id":r.get("indicator_id"),"period":r.get("period"),"value":r.get("value"),"unit":r.get("unit"),"source_id":r.get("source_id"),"corroboration_source_ids":r.get("corroboration_source_ids",[])} for r in additions],"notes":["A complete two-source corroborated SBV policy-rate event passed the automatic repository gate."]}
    write_json(report_dir/"policy-rates-auto-persistence.json",report); return report


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--incoming-dir",required=True); ap.add_argument("--repo-processed-dir",default="data/processed/macro"); ap.add_argument("--report-dir",default="data/staging/policy-rates-auto-persistence"); ap.add_argument("--source-run-number",required=True,type=int); ap.add_argument("--source-run-database-id",required=True); ap.add_argument("--policy",default="config/policy_rates_auto_persistence_policy.json"); ap.add_argument("--gate",default="config/policy_rates_production_gate.json"); args=ap.parse_args()
    resolve=lambda v: Path(v) if Path(v).is_absolute() else ROOT/v; repo=resolve(args.repo_processed_dir); report=resolve(args.report_dir)
    if repo.resolve() != (ROOT/"data/processed/macro").resolve(): raise SystemExit("Safety violation: invalid repository target")
    if report.resolve() != (ROOT/"data/staging/policy-rates-auto-persistence").resolve(): raise SystemExit("Safety violation: invalid report target")
    result=build_policy_rates_persistence(resolve(args.incoming_dir),repo,report,args.source_run_number,args.source_run_database_id,resolve(args.policy),resolve(args.gate)); print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
