from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from collectors.vietnamplus_customer_rates import parse_vietnamplus_customer_rates, discover_vietnamplus_customer_rates_url
from candidate_pipeline import build_publish_readiness

html=(ROOT/'tests/fixtures/vietnamplus_customer_rates_sample.html').read_text(encoding='utf-8')
rows=parse_vietnamplus_customer_rates(html,'https://www.vietnamplus.vn/example.vnp','2026-10-05T00:00:00+00:00')
assert len(rows)==5, rows
by={r['indicator_id']:r for r in rows}
assert by['deposit-rate-vnd-6-12m-low']['value']==6.5
assert by['deposit-rate-vnd-6-12m-high']['value']==8.0
assert by['lending-rate-vnd-average-low']['value']==8.4
assert by['lending-rate-vnd-average-high']['value']==10.7
assert by['priority-short-term-lending-rate-vnd']['value']==4.0
assert all(r['period']=='2026-08' for r in rows)
assert all(r['source_id']=='vna-vietnamplus' and r['evidence_status']=='reported' for r in rows)
listing=(ROOT/'tests/fixtures/vietnamplus_customer_rates_listing_sample.html').read_text(encoding='utf-8')
url=discover_vietnamplus_customer_rates_url(listing,'https://www.vietnamplus.vn/tag/ngan-hang-tag3047.vnp')
assert url and 'post1137474' in url, url

cfg=json.loads((ROOT/'config/source_pools.json').read_text(encoding='utf-8'))
pool=next(p for p in cfg['pools'] if p['id']=='customer-rates')
assert pool['fallback_source_ids']==['vnba','vna-vietnamplus']
assert pool['corroboration_tolerance_abs']==0.01

# Simulate candidate history with both independent fallback sources for the same period.
vnba=[]
for iid,val in {
    'deposit-rate-vnd-6-12m-low':6.5,
    'deposit-rate-vnd-6-12m-high':8.0,
    'lending-rate-vnd-average-low':8.4,
    'lending-rate-vnd-average-high':10.7,
    'priority-short-term-lending-rate-vnd':3.9,
}.items():
    vnba.append({'id':'vnba-'+iid,'indicator_id':iid,'period':'2026-08','period_type':'month','value':val,'unit':'percent-per-year','source_id':'vnba','source_url':'https://vnba.example','published_at':'2026-09-25','fetched_at':'2026-10-05T00:00:00+00:00','evidence_status':'reported'})
for r in rows:
    r=dict(r); r['id']='vnp-'+r['indicator_id']
    by[r['indicator_id']]=r
combined=vnba+[dict(r,id='vnp-'+r['indicator_id']) for r in rows]
ready=build_publish_readiness(combined,'2026-10-05T00:00:00+00:00')['data']
states={r['indicator_id']:r for r in ready}
for iid in ['deposit-rate-vnd-6-12m-low','deposit-rate-vnd-6-12m-high','lending-rate-vnd-average-low','lending-rate-vnd-average-high']:
    assert states[iid]['status']=='ready-corroborated', states[iid]
    assert states[iid]['independent_sources']==['vnba','vna-vietnamplus'], states[iid]
# 3.9 vs VietnamPlus's rounded ~4.0 is intentionally NOT silently reconciled.
assert states['priority-short-term-lending-rate-vnd']['status']=='evidence-only', states['priority-short-term-lending-rate-vnd']
print('Phase 4.2J.2 VietnamPlus customer-rates corroboration tests PASS')
