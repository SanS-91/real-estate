from pathlib import Path
import json,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
projects=json.loads((ROOT/'data/mock/market/projects.json').read_text(encoding='utf-8'))
devs=json.loads((ROOT/'data/mock/core/developers.json').read_text(encoding='utf-8'))
sources=json.loads((ROOT/'data/mock/core/sources.json').read_text(encoding='utf-8'))
obs=json.loads((ROOT/'data/mock/market/observations.json').read_text(encoding='utf-8'))

ids={x['id'] for x in projects['data']}
assert projects['record_count']==len(projects['data'])==13
assert {'vinhomes-grand-park','the-9-stellars','celesta-gold','essensia-parkway'} <= ids
assert devs['record_count']==len(devs['data'])==9
source_ids={x['id'] for x in sources['data']}
assert {'vinhomes-official','sonkim-land-official','keppel-real-estate-vietnam','phu-long-official','nomura-real-estate-vietnam'} <= source_ids
assert all(x.get('primary_source_id') in source_ids for x in projects['data'])
assert all(x.get('official_url','').startswith('http') for x in projects['data'])
assert not any(k in x for x in projects['data'] for k in ('average_asp','absorption_rate','sales_units','new_supply'))
assert obs['record_count']==len(obs['data']) and obs['record_count']>=7

tmp=Path(tempfile.mkdtemp())/'coverage.json'
cp=subprocess.run([sys.executable,str(ROOT/'scripts/build_market_coverage.py'),'--output',str(tmp)],cwd=ROOT,capture_output=True,text=True)
assert cp.returncode==0,cp.stdout+'\n'+cp.stderr
out=json.loads(tmp.read_text(encoding='utf-8'))
assert out['status']=='pass'
assert out['counts']['projects']==13
assert out['counts']['developers']==9
assert out['first_party_project_share']==1.0
print('Phase 4.7 market coverage tests PASS')
