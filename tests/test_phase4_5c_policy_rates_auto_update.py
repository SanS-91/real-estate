from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json, shutil, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from persist_policy_rates import build_policy_rates_persistence
IDS={'policy-refinancing-rate':4.25,'policy-rediscount-rate':2.75,'policy-overnight-lending-rate':4.75}
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,obj): p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 policy=load(ROOT/'config/policy_rates_auto_persistence_policy.json'); gate=load(ROOT/'config/policy_rates_production_gate.json')
 assert set(policy['allowed_indicator_ids'])==set(IDS); assert set(gate['allowed_indicators'])==set(IDS); assert policy['required_bundle_size']==3
 wf=(ROOT/'.github/workflows/macro-candidate.yml').read_text(encoding='utf-8'); assert '30 4 * * 4' in wf and 'persist-policy-rates-production:' in wf
 current=load(ROOT/'data/processed/macro/observations.json'); meta=load(ROOT/'data/processed/macro/repository-publish.json'); rows=deepcopy(current['data']); event='2026-10-07'
 latest={}
 for r in current['data']:
  if r.get('indicator_id') in IDS and (r.get('indicator_id') not in latest or r['period']>latest[r['indicator_id']]['period']): latest[r['indicator_id']]=r
 for i,(iid,val) in enumerate(IDS.items(),1):
  r=deepcopy(latest[iid]); r.update({'id':f'p45c-{i}-{event}','source_record_id':f'p45c-{i}-{event}','period':event,'data_date':event,'value':val,'source_id':'vna-vietnamplus','source_url':'https://www.vietnamplus.vn/fixture.vnp','published_at':'2026-10-07','fetched_at':'2026-10-07T04:30:00+00:00','evidence_status':'corroborated','corroboration_source_ids':['vna-vietnamplus','banking-times-vn'],'corroboration_observation_ids':[f'p45c-{i}-a',f'p45c-{i}-b'],'observation_status':'final','promoted_at':'2026-10-07T04:31:00+00:00','promotion_run_id':'phase45c-test'}); rows.append(r)
 rows.sort(key=lambda r:(r.get('indicator_id',''),r.get('period',''),r.get('id','')))
 incoming={'schema_version':1,'generated_at':'2026-10-07T04:31:00+00:00','record_count':len(rows),'production_write':True,'repository_publish':False,'frontend_publish':False,'source_run_id':'phase45c-test','data':rows}
 run={'schema_version':1,'generated_at':'2026-10-07T04:31:00+00:00','mode':'controlled-production-v1','production_write':True,'repository_publish':False,'frontend_publish':False,'source_run_id':'phase45c-test','prior_record_count':len(current['data']),'added_record_count':3,'unchanged_record_count':0,'held_record_count':0,'conflict_count':0,'final_record_count':len(rows)}
 tmp=Path(tempfile.mkdtemp(prefix='p45c-'))
 try:
  repo=tmp/'repo'; inc=tmp/'incoming'; dump(repo/'observations.json',current); dump(repo/'repository-publish.json',meta); dump(inc/'observations.json',incoming); dump(inc/'promotion-run.json',run); source_run=max(1100,int(meta.get('source_run_number',0))+1)
  result=build_policy_rates_persistence(inc,repo,tmp/'report',source_run,'p45c-db',ROOT/'config/policy_rates_auto_persistence_policy.json',ROOT/'config/policy_rates_production_gate.json',datetime(2026,10,7,11,30,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh')))
  assert result['status']=='ready-to-commit' and result['added_record_count']==3 and result['period']==event
  out=load(repo/'observations.json'); assert out['record_count']==current['record_count']+3 and out['repository_persistence_mode']=='controlled-policy-rates-auto-persistence-v1'
  bad=deepcopy(incoming); bad['data']=[r for r in bad['data'] if not str(r.get('id','')).startswith('p45c-3-')]; bad['record_count']-=1; badrun=deepcopy(run); badrun['added_record_count']=2; badrun['final_record_count']-=1
  repo2=tmp/'repo2'; inc2=tmp/'inc2'; dump(repo2/'observations.json',current); dump(repo2/'repository-publish.json',meta); dump(inc2/'observations.json',bad); dump(inc2/'promotion-run.json',badrun)
  try: build_policy_rates_persistence(inc2,repo2,tmp/'report2',source_run+1,'p45c-bad',ROOT/'config/policy_rates_auto_persistence_policy.json',ROOT/'config/policy_rates_production_gate.json',datetime(2026,10,7,11,30,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh')))
  except ValueError as exc: assert 'complete three-rate event' in str(exc)
  else: raise AssertionError('Partial policy event was not blocked')
 finally: shutil.rmtree(tmp,ignore_errors=True)
 print('Phase 4.5C policy-rate auto-update tests PASS')
if __name__=='__main__': main()
