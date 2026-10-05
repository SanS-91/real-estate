from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from collectors.sbv_policy_archive import parse_sbv_policy_archive
from collectors.vietnamplus_interbank_rates import parse_vietnamplus_interbank_rates, discover_vietnamplus_interbank_rates_url


def test_policy_archive_parser():
    html=(ROOT/'tests/fixtures/sbv_policy_archive_sample.html').read_text(encoding='utf-8')
    rows=parse_sbv_policy_archive(html,'https://www.sbv.gov.vn/documents/d/sbv_portal/590044','2026-10-05T00:00:00Z')
    assert len(rows)==3
    vals={r['indicator_id']:r['value'] for r in rows}
    assert vals=={'policy-refinancing-rate':4.5,'policy-rediscount-rate':3.0,'policy-overnight-lending-rate':5.0}
    assert {r['evidence_status'] for r in rows}=={'reported'}
    assert {r['source_id'] for r in rows}=={'sbv-vietnam-archive'}
    assert {r['period'] for r in rows}=={'2023-12'}


def test_vietnamplus_interbank_parser_and_discovery():
    listing=(ROOT/'tests/fixtures/vietnamplus_interbank_listing_sample.html').read_text(encoding='utf-8')
    url=discover_vietnamplus_interbank_rates_url(listing,'https://www.vietnamplus.vn/ngan-hang-tag708050.vnp')
    assert url and 'lai-suat-lien-ngan-hang' in url
    html=(ROOT/'tests/fixtures/vietnamplus_interbank_rates_sample.html').read_text(encoding='utf-8')
    rows=parse_vietnamplus_interbank_rates(html,url,'2026-10-05T00:00:00Z')
    assert len(rows)==1
    r=rows[0]
    assert r['indicator_id']=='interbank-on'
    assert r['value']==1.2
    assert r['data_date']=='2026-08-27'
    assert r['evidence_status']=='reported'
    assert r['source_id']=='vna-vietnamplus'


def test_pool_fallback_policy():
    pools=json.loads((ROOT/'config/source_pools.json').read_text(encoding='utf-8'))['pools']
    by={p['id']:p for p in pools}
    assert by['policy-rates']['fallback_source_ids']==['sbv-vietnam-archive']
    assert by['interbank-market']['fallback_source_ids']==['vna-vietnamplus']
    assert by['policy-rates']['min_independent_sources_for_corroborated']==2
    assert by['interbank-market']['min_independent_sources_for_corroborated']==2


def test_workflow_has_fallback_gate():
    wf=(ROOT/'.github/workflows/macro-candidate.yml').read_text(encoding='utf-8')
    assert 'policy-liquidity-fallback' in wf
    assert '--source sbv-policy-archive' in wf
    assert '--source vietnamplus-interbank-rates' in wf

if __name__=='__main__':
    test_policy_archive_parser(); test_vietnamplus_interbank_parser_and_discovery(); test_pool_fallback_policy(); test_workflow_has_fallback_gate(); print('Phase 4.2K.1.1 fallback tests passed.')
