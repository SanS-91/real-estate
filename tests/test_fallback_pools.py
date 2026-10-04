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

    # VietnamPlus + Thoi Bao Ngan Hang can independently corroborate the same SBV rate.
    r=build_publish_readiness([
        row('usd-vnd-central-rate',25636,'vna-vietnamplus'),
        row('usd-vnd-central-rate',25636,'banking-times-vn'),
    ], NOW)
    states={x['indicator_id']:x for x in r['data']}
    assert states['usd-vnd-central-rate']['status']=='ready-corroborated'
    assert set(states['usd-vnd-central-rate']['independent_sources'])=={'vna-vietnamplus','banking-times-vn'}

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

    # Two independent media trackers agreeing on the same SJC quote can corroborate it.
    r=build_publish_readiness([
        row('sjc-gold-bar-buy',140_500_000,'baonghean-gold','2026-10-04'),
        row('sjc-gold-bar-buy',140_500_000,'vietnamnet-gold','2026-10-04'),
        row('sjc-gold-bar-sell',143_500_000,'baonghean-gold','2026-10-04'),
        row('sjc-gold-bar-sell',143_500_000,'vietnamnet-gold','2026-10-04'),
    ], NOW)
    states={x['indicator_id']:x for x in r['data']}
    assert states['sjc-gold-bar-buy']['status']=='ready-corroborated'
    assert states['sjc-gold-bar-sell']['status']=='ready-corroborated'

    # A trusted-media gold tracker is usable evidence but not canonical by itself.
    r=build_publish_readiness([
        row('sjc-gold-bar-sell',143_500_000,'baonghean-gold','2026-10-04',status='reported'),
    ], NOW)
    states={x['indicator_id']:x for x in r['data']}
    assert states['sjc-gold-bar-sell']['status']=='evidence-only'

    print('Fallback pool tests passed')

if __name__=='__main__':
    main()
