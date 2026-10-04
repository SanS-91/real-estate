from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from candidate_pipeline import build_publish_readiness

NOW='2026-10-04T00:00:00+00:00'

def row(iid, value, source, date='2026-10-02', status='reported'):
    return {
        'id': f'{iid}-{source}-{value}', 'indicator_id': iid, 'value': value,
        'unit': 'vnd-per-usd' if 'usd-vnd' in iid else ('vnd-per-tael' if 'gold' in iid else 'percent'),
        'source_id': source, 'data_date': date if iid=='usd-vnd-central-rate' or 'gold' in iid else None,
        'period': date if iid=='usd-vnd-central-rate' or 'gold' in iid else '2026-09',
        'published_at': date, 'fetched_at': NOW, 'evidence_status': status,
    }

def main():
    # One fallback source => evidence only.
    r=build_publish_readiness([row('usd-vnd-central-rate',25636,'vna-vietnamplus')], NOW)
    states={x['indicator_id']:x for x in r['data']}
    assert states['usd-vnd-central-rate']['status']=='evidence-only'

    # Two independent fallback sources agreeing => corroborated candidate.
    r=build_publish_readiness([
        row('usd-vnd-central-rate',25636,'vna-vietnamplus'),
        row('usd-vnd-central-rate',25636,'vov'),
    ], NOW)
    states={x['indicator_id']:x for x in r['data']}
    assert states['usd-vnd-central-rate']['status']=='ready-corroborated'

    # Preferred direct verified source always wins.
    r=build_publish_readiness([
        row('usd-vnd-central-rate',25636,'vna-vietnamplus'),
        row('usd-vnd-central-rate',25636,'sbv-vietnam',status='verified'),
    ], NOW)
    states={x['indicator_id']:x for x in r['data']}
    assert states['usd-vnd-central-rate']['status']=='ready-canonical'

    # Gold fallback quote works as evidence and two issuers can corroborate.
    r=build_publish_readiness([
        row('sjc-gold-bar-sell',147_600_000,'pnj-gold','2026-10-04',status='corroborated'),
        row('sjc-gold-bar-sell',147_600_000,'doji-gold','2026-10-04',status='corroborated'),
    ], NOW)
    states={x['indicator_id']:x for x in r['data']}
    assert states['sjc-gold-bar-sell']['status']=='ready-corroborated'
    print('Fallback pool tests passed')

if __name__=='__main__':
    main()
