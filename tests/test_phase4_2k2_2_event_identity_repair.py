from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from candidate_pipeline import merge_records, build_publish_readiness

POLICY_IDS = [
    'policy-refinancing-rate',
    'policy-rediscount-rate',
    'policy-overnight-lending-rate',
]
VALUES = {
    'policy-refinancing-rate': 4.5,
    'policy-rediscount-rate': 3.0,
    'policy-overnight-lending-rate': 5.0,
}


def row(iid, source, period, rid, suffix):
    return {
        'id': f'{source}-{iid}-{suffix}',
        'indicator_id': iid,
        'period': period,
        'period_type': 'date',
        'data_date': period,
        'value': VALUES[iid],
        'unit': 'percent-per-year',
        'source_id': source,
        'source_record_id': rid,
        'evidence_status': 'reported',
        'published_at': '2023-06-16',
        'fetched_at': '2026-10-06T00:00:00Z',
    }


def test_same_source_event_reparse_supersedes_stale_cached_period():
    # Simulate the bad cached VietnamPlus parse from 4.2K.2 where the same
    # Decision 1123 event was mistakenly assigned a 2026 sidebar date.
    existing = [
        row(iid, 'vna-vietnamplus', '2026-10-01', '1123/QĐ-NHNN', 'stale')
        for iid in POLICY_IDS
    ]
    incoming = [
        row(iid, 'vna-vietnamplus', '2023-06-19', '1123/QĐ-NHNN', 'corrected')
        for iid in POLICY_IDS
    ]
    merged = merge_records(existing, incoming)
    assert len(merged) == 3
    assert {r['period'] for r in merged} == {'2023-06-19'}
    assert all(r['id'].endswith('-corrected') for r in merged)


def test_corrected_event_then_corroborates_across_independent_sources():
    stale = [
        row(iid, 'vna-vietnamplus', '2026-10-01', '1123/QĐ-NHNN', 'stale')
        for iid in POLICY_IDS
    ]
    fresh = []
    for source in ['vna-vietnamplus', 'gov-vietnam-baochinhphu', 'banking-times-vn']:
        fresh.extend([
            row(iid, source, '2023-06-19', '1123/QĐ-NHNN', source)
            for iid in POLICY_IDS
        ])
    merged = merge_records(stale, fresh)
    readiness = build_publish_readiness(merged, '2026-10-06T00:00:00Z')
    by = {x['indicator_id']: x for x in readiness['data']}
    for iid in POLICY_IDS:
        assert by[iid]['status'] == 'ready-corroborated'
        assert by[iid]['latest_business_period'] == '2023-06-19'
        assert len(by[iid]['independent_sources']) == 3


def test_genuinely_new_event_with_different_record_id_is_not_silently_removed():
    old = [
        row(iid, 'vna-vietnamplus', '2023-06-19', '1123/QĐ-NHNN', 'old')
        for iid in POLICY_IDS
    ]
    new = [
        row(iid, 'vna-vietnamplus', '2026-10-15', '2000/QĐ-NHNN', 'new')
        for iid in POLICY_IDS
    ]
    merged = merge_records(old, new)
    # Different policy decision => both events stay in history.
    assert len(merged) == 6
    assert {r['source_record_id'] for r in merged} == {'1123/QĐ-NHNN', '2000/QĐ-NHNN'}


if __name__ == '__main__':
    test_same_source_event_reparse_supersedes_stale_cached_period()
    test_corrected_event_then_corroborates_across_independent_sources()
    test_genuinely_new_event_with_different_record_id_is_not_silently_removed()
    print('Phase 4.2K.2.2 event identity repair tests passed')
