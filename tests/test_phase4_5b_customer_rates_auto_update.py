from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json, shutil, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from persist_customer_rates import build_customer_rates_persistence

IDS={
 'deposit-rate-vnd-6-12m-low':6.6,
 'deposit-rate-vnd-6-12m-high':8.1,
 'lending-rate-vnd-average-low':8.5,
 'lending-rate-vnd-average-high':10.8,
}
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,obj):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def next_month(period):
 dt=datetime.strptime(period,'%Y-%m'); y,m=dt.year,dt.month
 return f'{y+1:04d}-01' if m==12 else f'{y:04d}-{m+1:02d}'

def main():
 policy=load(ROOT/'config/customer_rates_auto_persistence_policy.json'); gate=load(ROOT/'config/customer_rates_production_gate.json')
 assert set(policy['allowed_indicator_ids'])==set(IDS); assert set(gate['allowed_indicators'])==set(IDS)
 assert policy['required_bundle_size']==4 and policy['max_additions_per_run']==4
 wf=(ROOT/'.github/workflows/macro-candidate.yml').read_text(encoding='utf-8')
 assert "15 4 * * 2" in wf and 'persist-customer-rates-production:' in wf and '--policy config/customer_rates_production_gate.json' in wf
 current=load(ROOT/'data/processed/macro/observations.json'); meta=load(ROOT/'data/processed/macro/repository-publish.json')
 latest={}
 for r in current['data']:
  if r.get('indicator_id') in IDS and (r.get('indicator_id') not in latest or r['period']>latest[r['indicator_id']]['period']): latest[r['indicator_id']]=r
 period=next_month(max(r['period'] for r in latest.values()))
 rows=deepcopy(current['data'])
 for i,(iid,val) in enumerate(IDS.items(),1):
  r=deepcopy(latest[iid]); r.update({'id':f'p45b-{i}-{period}','source_record_id':f'p45b-{i}-{period}','period':period,'value':val,'source_id':'vnba','source_url':'https://vnba.org.vn/fixture','published_at':period+'-25' if False else '2026-10-01','fetched_at':'2026-10-05T04:00:00+00:00','evidence_status':'corroborated','corroboration_source_ids':['vnba','vna-vietnamplus'],'corroboration_observation_ids':[f'p45b-{i}-a',f'p45b-{i}-b'],'observation_status':'final','promoted_at':'2026-10-05T04:01:00+00:00','promotion_run_id':'phase45b-test'})
  rows.append(r)
 rows.sort(key=lambda r:(r.get('indicator_id',''),r.get('period',''),r.get('id','')))
 incoming={'schema_version':1,'generated_at':'2026-10-05T04:01:00+00:00','record_count':len(rows),'production_write':True,'repository_publish':False,'frontend_publish':False,'source_run_id':'phase45b-test','data':rows}
 run={'schema_version':1,'generated_at':'2026-10-05T04:01:00+00:00','mode':'controlled-production-v1','production_write':True,'repository_publish':False,'frontend_publish':False,'source_run_id':'phase45b-test','prior_record_count':len(current['data']),'added_record_count':4,'unchanged_record_count':0,'held_record_count':0,'conflict_count':0,'final_record_count':len(rows)}
 tmp=Path(tempfile.mkdtemp(prefix='p45b-'))
 try:
  repo=tmp/'repo'; inc=tmp/'incoming'; report=tmp/'report'; dump(repo/'observations.json',current); dump(repo/'repository-publish.json',meta); dump(inc/'observations.json',incoming); dump(inc/'promotion-run.json',run)
  source_run=max(1000,int(meta.get('source_run_number',0))+1)
  result=build_customer_rates_persistence(inc,repo,report,source_run,'p45b-db',ROOT/'config/customer_rates_auto_persistence_policy.json',ROOT/'config/customer_rates_production_gate.json',datetime(2026,10,7,11,15,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh')))
  assert result['status']=='ready-to-commit' and result['added_record_count']==4 and result['period']==period
  out=load(repo/'observations.json'); assert out['record_count']==current['record_count']+4 and out['repository_persistence_mode']=='controlled-customer-rates-auto-persistence-v1'
  # Partial bundle must fail.\n  bad=deepcopy(incoming); bad['data']=[r for r in bad['data'] if not str(r.get('id','')).startswith('p45b-4-')]; bad['record_count']-=1; badrun=deepcopy(run); badrun['added_record_count']=3; badrun['final_record_count']-=1
  repo2=tmp/'repo2'; inc2=tmp/'inc2'; dump(repo2/'observations.json',current); dump(repo2/'repository-publish.json',meta); dump(inc2/'observations.json',bad); dump(inc2/'promotion-run.json',badrun)
  try: build_customer_rates_persistence(inc2,repo2,tmp/'report2',source_run+1,'p45b-bad',ROOT/'config/customer_rates_auto_persistence_policy.json',ROOT/'config/customer_rates_production_gate.json',datetime(2026,10,7,11,15,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh')))
  except ValueError as exc: assert 'complete four-component bundle' in str(exc)
  else: raise AssertionError('Partial customer-rate bundle was not blocked')
 finally: shutil.rmtree(tmp,ignore_errors=True)
 print('Phase 4.5B customer-rate auto-update tests PASS')
if __name__=='__main__': main()
