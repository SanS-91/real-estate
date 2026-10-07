#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GROUPS={
 'daily-fx-gold': {'usd-vnd-central-rate','sjc-gold-buy','sjc-gold-sell'},
 'monthly-official': {'cpi-yoy','cpi-mom','core-cpi-yoy','credit-growth-ytd','bank-funding-growth-ytd'},
 'customer-rates': {'deposit-rate-vnd-6-12m-low','deposit-rate-vnd-6-12m-high','lending-rate-vnd-average-low','lending-rate-vnd-average-high'},
 'policy-rates': {'policy-refinancing-rate','policy-rediscount-rate','policy-overnight-lending-rate'},
}
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output',default='data/state/phase45-operational-qa.json'); args=ap.parse_args()
 obs=load(ROOT/'data/processed/macro/observations.json'); rows=obs.get('data',[]); errors=[]; keys=set(); ids=set()
 if obs.get('record_count')!=len(rows): errors.append('record_count mismatch')
 for r in rows:
  rid=r.get('id'); key=(r.get('indicator_id'),r.get('period_type'),r.get('period'))
  if not rid or rid in ids: errors.append(f'duplicate/missing id: {rid}')
  ids.add(rid)
  if key in keys: errors.append(f'duplicate logical key: {key}')
  keys.add(key)
 coverage={name:sorted(set(r.get('indicator_id') for r in rows)&iids) for name,iids in GROUPS.items()}
 for name,iids in GROUPS.items():
  missing=iids-set(coverage[name])
  if missing: errors.append(f'{name} missing baseline indicators: {sorted(missing)}')
 policies=['daily_auto_persistence_policy.json','monthly_auto_persistence_policy.json','customer_rates_auto_persistence_policy.json','policy_rates_auto_persistence_policy.json']
 for f in policies:
  p=load(ROOT/'config'/f)
  if p.get('repository_publish') is not True or p.get('frontend_publish') is not False: errors.append(f'{f}: unsafe publish flags')
 result={'schema_version':1,'status':'pass' if not errors else 'fail','record_count':len(rows),'groups':coverage,'errors':errors}
 out=ROOT/args.output; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('# Phase 4.5 Operational QA'); print(); print(f"**Status:** `{result['status']}` · Canonical records {len(rows)}")
 for name,vals in coverage.items(): print(f"- {name}: {len(vals)}/{len(GROUPS[name])} baseline indicators present")
 if errors:
  for e in errors: print(f'- ERROR: {e}')
  raise SystemExit(1)
 print('- Append-only logical-key baseline is clean; all automatic gates remain repository-only and frontend-safe.')
if __name__=='__main__': main()
