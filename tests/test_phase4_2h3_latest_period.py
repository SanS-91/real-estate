from pathlib import Path
import json
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from candidate_pipeline import build_publish_readiness
from promotion_preview import build_preview

PREVIEW_POLICY = ROOT / 'config/promotion_policy.json'
FRONTEND_MAPPING = ROOT / 'config/frontend_indicator_map.json'
NORMALIZATION = ROOT / 'config/indicator_normalization.json'


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def obs(rid, source, value, period, fetched_at):
    return {
        'id': rid,
        'indicator_id': 'usd-vnd-central-rate',
        'period': period,
        'period_type': 'day',
        'data_date': period,
        'value': value,
        'unit': 'vnd-per-usd',
        'source_id': source,
        'source_url': f'https://example.test/{source}/{period}',
        'published_at': f'{period}T08:00:00+07:00',
        'fetched_at': fetched_at,
        'evidence_status': 'reported',
        'observation_status': 'candidate',
        'methodology_note': 'fixture',
    }


def item_for(readiness, iid):
    return next(x for x in readiness['data'] if x['indicator_id'] == iid)


def main():
    # Historical period is strongly corroborated, but the latest period has only one source.
    # Resolver MUST stay on the latest period and mark it evidence-only; it must not fall back
    # to the older corroborated date merely because that date has stronger evidence depth.
    rows = [
        obs('fx-old-a', 'banking-times-vn', 25636, '2026-10-02', '2026-10-02T02:00:00+00:00'),
        obs('fx-old-b', 'vna-vietnamplus', 25636, '2026-10-02', '2026-10-02T02:01:00+00:00'),
        obs('fx-new-a', 'banking-times-vn', 25643, '2026-10-05', '2026-10-05T02:50:00+00:00'),
    ]
    readiness = build_publish_readiness(rows, '2026-10-05T03:00:00+00:00')
    fx = item_for(readiness, 'usd-vnd-central-rate')
    assert fx['status'] == 'evidence-only', fx
    assert fx['latest_business_period'] == '2026-10-05', fx
    assert fx['selected_observation_id'] == 'fx-new-a', fx
    assert fx['evidence_observation_ids'] == ['fx-new-a'], fx
    assert fx['independent_sources'] == ['banking-times-vn'], fx

    temp = Path(tempfile.mkdtemp(prefix='phase4-2h3-latest-period-'))
    staging = ROOT / 'data/staging/test-h3-preview'
    shutil.rmtree(staging, ignore_errors=True)
    try:
        candidate_dir = temp / 'candidate'
        dump(candidate_dir / 'observations.json', {
            'schema_version': 1,
            'generated_at': '2026-10-05T03:00:00+00:00',
            'record_count': len(rows),
            'candidate_only': True,
            'data': rows,
        })
        dump(candidate_dir / 'publish-readiness.json', readiness)
        dump(candidate_dir / 'run-report.json', {
            'schema_version': 1,
            'run_id': 'fixture-h3-latest-period',
            'status': 'pass',
        })
        build_preview(candidate_dir, staging, PREVIEW_POLICY, FRONTEND_MAPPING, NORMALIZATION)
        manifest = load(staging / 'promotion-manifest.json')
        fxm = next(x for x in manifest['data'] if x['indicator_id'] == 'usd-vnd-central-rate')
        assert fxm['action'] == 'hold-evidence', fxm
        assert fxm['period'] == '2026-10-05', fxm
        assert fxm['value'] == 25643, fxm
        assert fxm['source_id'] == 'banking-times-vn', fxm
        assert fxm['latest_business_period'] == '2026-10-05', fxm

        evidence = load(staging / 'evidence-observations.preview.json')['data']
        fx_evidence = [x for x in evidence if x['indicator_id'] == 'usd-vnd-central-rate']
        assert len(fx_evidence) == 1, fx_evidence
        assert fx_evidence[0]['period'] == '2026-10-05', fx_evidence
        assert fx_evidence[0]['value'] == 25643, fx_evidence
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(temp, ignore_errors=True)

    # Once a second independent source appears for the SAME latest date, it may upgrade
    # to ready-corroborated. Historical corroboration is irrelevant to that decision.
    rows2 = rows + [
        obs('fx-new-b', 'vna-vietnamplus', 25643, '2026-10-05', '2026-10-05T02:55:00+00:00'),
    ]
    readiness2 = build_publish_readiness(rows2, '2026-10-05T03:05:00+00:00')
    fx2 = item_for(readiness2, 'usd-vnd-central-rate')
    assert fx2['status'] == 'ready-corroborated', fx2
    assert fx2['latest_business_period'] == '2026-10-05', fx2
    assert set(fx2['evidence_observation_ids']) == {'fx-new-a', 'fx-new-b'}, fx2
    assert set(fx2['independent_sources']) == {'banking-times-vn', 'vna-vietnamplus'}, fx2

    print('Phase 4.2H.3 latest-period resolver guard tests passed')


if __name__ == '__main__':
    main()
