from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from collectors.sbv_policy_rates import parse_sbv_policy_rates
from collectors.sbv_interbank_rates import parse_sbv_interbank_rates

html=(ROOT/'tests/fixtures/sbv_policy_rates_sample.html').read_text(encoding='utf-8')
rows=parse_sbv_policy_rates(html,'https://dttktt.sbv.gov.vn/policy','2026-10-05T00:00:00Z')
got={x['indicator_id']:x for x in rows}
assert len(rows)==3, rows
assert got['policy-refinancing-rate']['value']==4.5
assert got['policy-rediscount-rate']['value']==3.0
assert got['policy-overnight-lending-rate']['value']==5.0
assert all(x['evidence_status']=='verified' for x in rows)
assert all(x['period']=='2023-06-19' for x in rows)

html=(ROOT/'tests/fixtures/sbv_interbank_rates_sample.html').read_text(encoding='utf-8')
rows=parse_sbv_interbank_rates(html,'https://dttktt.sbv.gov.vn/interbank','2026-10-05T00:00:00Z')
assert len(rows)==1, rows
row=rows[0]
assert row['indicator_id']=='interbank-on'
assert row['value']==4.4, row
assert row['period']=='2026-10-02'
assert row['evidence_status']=='verified'

live=json.loads((ROOT/'config/live_sources.json').read_text(encoding='utf-8'))
keys={x['key'] for x in live['sources']}
assert {'sbv-policy-rates','sbv-interbank-rates'} <= keys
pools=json.loads((ROOT/'config/source_pools.json').read_text(encoding='utf-8'))
ids={x['id'] for x in pools['pools']}
assert {'policy-rates','interbank-market'} <= ids
wf=(ROOT/'.github/workflows/macro-candidate.yml').read_text(encoding='utf-8')
assert '- policy-liquidity-discovery' in wf
print('Phase 4.2K.1 policy/interbank discovery tests PASS')
