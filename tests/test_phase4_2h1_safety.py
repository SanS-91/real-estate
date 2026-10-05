from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from candidate_pipeline import build_publish_readiness

NOW='2026-10-04T16:00:00+00:00'

def row(iid, value, source, date, unit):
    return {
        'id': f'{iid}-{source}-{date}-{value}',
        'indicator_id': iid,
        'value': value,
        'unit': unit,
        'source_id': source,
        'data_date': date,
        'period': date,
        'period_type': 'day',
        'published_at': date,
        'fetched_at': NOW,
        'evidence_status': 'reported',
    }

def main():
    rows = [
        row('usd-vnd-central-rate', 25636, 'vna-vietnamplus', '2026-10-02', 'vnd-per-usd'),
        row('usd-vnd-central-rate', 25636, 'banking-times-vn', '2026-10-02', 'vnd-per-usd'),
        row('sjc-gold-bar-buy', 140_500_000, 'baonghean-gold', '2026-10-04', 'vnd-per-tael'),
        row('sjc-gold-bar-buy', 140_500_000, 'vietnamnet-gold', '2026-10-04', 'vnd-per-tael'),
        row('sjc-gold-bar-sell', 143_500_000, 'baonghean-gold', '2026-10-04', 'vnd-per-tael'),
        row('sjc-gold-bar-sell', 143_500_000, 'vietnamnet-gold', '2026-10-04', 'vnd-per-tael'),
    ]
    readiness = build_publish_readiness(rows, NOW)
    states = {x['indicator_id']: x['status'] for x in readiness['data']}
    assert states['usd-vnd-central-rate'] == 'ready-corroborated'
    assert states['sjc-gold-bar-buy'] == 'ready-corroborated'
    assert states['sjc-gold-bar-sell'] == 'ready-corroborated'

    production = json.loads((ROOT/'config/production_promotion_policy.json').read_text(encoding='utf-8'))
    assert production['repository_publish'] is False
    assert production['frontend_publish'] is False

    print('Phase 4.2H.1 corroboration readiness tests passed')

if __name__ == '__main__':
    main()
