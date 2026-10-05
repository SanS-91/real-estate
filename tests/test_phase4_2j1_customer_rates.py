from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from collectors.sbv_customer_rates import (
    parse_sbv_customer_rates,
    discover_sbv_customer_rates_url,
    discover_sbv_customer_rates_attachment,
)

NOW = '2026-10-05T09:00:00+00:00'
FIX = ROOT / 'tests/fixtures'


def main():
    rows = parse_sbv_customer_rates(
        (FIX / 'sbv_customer_rates_sample.html').read_text(encoding='utf-8'),
        'https://www.sbv.gov.vn/documents/d/sbv_portal/lai-suat-thang-8-2026.pdf?download=true',
        NOW,
    )
    by = {x['indicator_id']: x for x in rows}
    assert len(rows) == 5, rows
    assert by['deposit-rate-vnd-6-12m-low']['value'] == 6.5
    assert by['deposit-rate-vnd-6-12m-high']['value'] == 8.0
    assert by['lending-rate-vnd-average-low']['value'] == 8.4
    assert by['lending-rate-vnd-average-high']['value'] == 10.7
    assert by['priority-short-term-lending-rate-vnd']['value'] == 4.0
    assert all(x['source_id'] == 'sbv-vietnam' for x in rows)
    assert all(x['evidence_status'] == 'verified' for x in rows)
    assert all(x['period'] == '2026-08' and x['period_type'] == 'month' for x in rows)

    listing = (FIX / 'sbv_customer_rates_listing_sample.html').read_text(encoding='utf-8')
    detail_url = discover_sbv_customer_rates_url(listing, 'https://www.sbv.gov.vn/')
    assert 'NEW' in detail_url
    detail = (FIX / 'sbv_customer_rates_detail_sample.html').read_text(encoding='utf-8')
    attachment = discover_sbv_customer_rates_attachment(detail, detail_url)
    assert attachment.endswith('lai-suat-thang-8-2026.pdf?download=true')

    pools = json.loads((ROOT/'config/source_pools.json').read_text(encoding='utf-8'))
    pool = next(x for x in pools['pools'] if x['id'] == 'customer-rates')
    assert pool['preferred_source_ids'] == ['sbv-vietnam']
    assert len(pool['indicator_ids']) == 5

    live = json.loads((ROOT/'config/live_sources.json').read_text(encoding='utf-8'))
    src = next(x for x in live['sources'] if x['key'] == 'sbv-customer-rates')
    assert src['canonical_eligible'] is True
    assert src['attachment_discoverer'] == 'discover_sbv_customer_rates_attachment'
    assert src['min_records'] == 5 and src['max_records'] == 5

    prod = json.loads((ROOT/'config/production_promotion_policy.json').read_text(encoding='utf-8'))
    range_ids = [
        'deposit-rate-vnd-6-12m-low',
        'deposit-rate-vnd-6-12m-high',
        'lending-rate-vnd-average-low',
        'lending-rate-vnd-average-high',
    ]
    for iid in range_ids:
        assert prod['allowed_indicators'][iid]['required_readiness_statuses'] == ['ready-corroborated']
        assert prod['allowed_indicators'][iid]['required_evidence_status'] == 'corroborated'
    assert 'priority-short-term-lending-rate-vnd' not in prod['allowed_indicators']

    fmap = json.loads((ROOT/'config/frontend_indicator_map.json').read_text(encoding='utf-8'))
    assert fmap['mappings']['deposit-rate-vnd-6-12m-low']['frontend_indicator_id'] == 'deposit-rate-vnd-6-12m-range'
    assert fmap['mappings']['deposit-rate-vnd-6-12m-high']['frontend_indicator_id'] == 'deposit-rate-vnd-6-12m-range'
    assert fmap['mappings']['lending-rate-vnd-average-low']['frontend_indicator_id'] == 'lending-rate-vnd-average-range'
    assert fmap['mappings']['lending-rate-vnd-average-high']['frontend_indicator_id'] == 'lending-rate-vnd-average-range'
    assert fmap['mappings']['priority-short-term-lending-rate-vnd']['frontend_indicator_id'] is None

    # Critical methodology guardrail: do not alias the official range to old demo scalars.
    assert 'deposit-rate-12m-average' not in pool['indicator_ids']
    assert 'lending-rate-average' not in pool['indicator_ids']

    print('Phase 4.2J.1 SBV customer-rates discovery/policy tests passed')

if __name__ == '__main__':
    main()
