from pathlib import Path
import json
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from promotion_preview import build_preview
from promote_production import build_production

PREVIEW_POLICY = ROOT / 'config/promotion_policy.json'
FRONTEND_MAPPING = ROOT / 'config/frontend_indicator_map.json'
NORMALIZATION = ROOT / 'config/indicator_normalization.json'
PRODUCTION_POLICY = ROOT / 'config/production_promotion_policy.json'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def dump(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def candidate(iid, source, value, unit, period, rid):
    return {
        'id': rid,
        'indicator_id': iid,
        'period': period,
        'period_type': 'day',
        'data_date': period,
        'value': value,
        'unit': unit,
        'source_id': source,
        'source_url': f'https://example.test/{source}',
        'published_at': f'{period}T08:00:00+07:00',
        'fetched_at': '2026-10-04T16:00:00+00:00',
        'evidence_status': 'reported',
        'observation_status': 'candidate',
        'methodology_note': 'fixture'
    }


def main():
    temp = Path(tempfile.mkdtemp(prefix='phase4-2h2-safety-'))
    staging = ROOT / 'data/staging/test-h2-preview'
    shutil.rmtree(staging, ignore_errors=True)
    try:
        candidate_dir = temp / 'candidate'
        rows = [
            candidate('usd-vnd-central-rate','banking-times-vn',25636,'vnd-per-usd','2026-10-02','fx-a'),
            candidate('usd-vnd-central-rate','vna-vietnamplus',25636,'vnd-per-usd','2026-10-02','fx-b'),
            candidate('sjc-gold-bar-buy','baonghean-gold',140_500_000,'vnd-per-tael','2026-10-04','gb-a'),
            candidate('sjc-gold-bar-buy','vietnamnet-gold',140_500_000,'vnd-per-tael','2026-10-04','gb-b'),
            candidate('sjc-gold-bar-sell','baonghean-gold',143_500_000,'vnd-per-tael','2026-10-04','gs-a'),
            candidate('sjc-gold-bar-sell','vietnamnet-gold',143_500_000,'vnd-per-tael','2026-10-04','gs-b'),
        ]
        dump(candidate_dir/'observations.json', {'schema_version':1,'generated_at':'2026-10-04T16:00:00+00:00','record_count':len(rows),'data':rows})
        readiness = [
            {'indicator_id':'usd-vnd-central-rate','status':'ready-corroborated','selected_observation_id':'fx-a','evidence_observation_ids':['fx-a','fx-b'],'independent_sources':['banking-times-vn','vna-vietnamplus'],'reason':'2 independent sources agree.'},
            {'indicator_id':'sjc-gold-bar-buy','status':'ready-corroborated','selected_observation_id':'gb-b','evidence_observation_ids':['gb-a','gb-b'],'independent_sources':['baonghean-gold','vietnamnet-gold'],'reason':'2 independent sources agree.'},
            {'indicator_id':'sjc-gold-bar-sell','status':'ready-corroborated','selected_observation_id':'gs-b','evidence_observation_ids':['gs-a','gs-b'],'independent_sources':['baonghean-gold','vietnamnet-gold'],'reason':'2 independent sources agree.'},
        ]
        dump(candidate_dir/'publish-readiness.json', {'schema_version':1,'generated_at':'2026-10-04T16:00:00+00:00','data':readiness})
        dump(candidate_dir/'run-report.json', {'schema_version':1,'run_id':'fixture-h2','status':'pass'})

        build_preview(candidate_dir, staging, PREVIEW_POLICY, FRONTEND_MAPPING, NORMALIZATION)
        canon = load(staging/'canonical-observations.preview.json')
        by = {r['indicator_id']: r for r in canon['data']}
        assert set(by) == {'usd-vnd-central-rate','sjc-gold-buy','sjc-gold-sell'}
        assert by['sjc-gold-buy']['source_indicator_id'] == 'sjc-gold-bar-buy'
        assert by['sjc-gold-sell']['source_indicator_id'] == 'sjc-gold-bar-sell'
        assert all(r['evidence_status'] == 'corroborated' for r in by.values())
        assert all(len(r['corroboration_source_ids']) == 2 for r in by.values())

        manifest = load(staging/'promotion-manifest.json')
        compat = {r['indicator_id']: r['frontend_compatibility'] for r in manifest['data']}
        assert compat['usd-vnd-central-rate'] == 'compatible'
        assert compat['sjc-gold-buy'] == 'compatible'
        assert compat['sjc-gold-sell'] == 'compatible'

        processed = temp/'processed'
        output, report = build_production(staging, processed, PRODUCTION_POLICY)
        assert output['record_count'] == 3
        assert report['added_record_count'] == 3
        assert report['held_record_count'] == 0
        assert all(r['evidence_status'] == 'corroborated' for r in output['data'])

        # Safety: one-source corroboration metadata must not enter production.
        bad = load(staging/'canonical-observations.preview.json')
        bad['data'][0]['corroboration_source_ids'] = bad['data'][0]['corroboration_source_ids'][:1]
        dump(staging/'canonical-observations.preview.json', bad)
        fresh = temp/'processed-bad'
        output_bad, report_bad = build_production(staging, fresh, PRODUCTION_POLICY)
        assert output_bad['record_count'] == 2
        assert any(x['action']=='hold-corroboration-depth' for x in report_bad['held'])

        print('Phase 4.2H.2 normalization/policy safety tests passed')
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(temp, ignore_errors=True)

if __name__ == '__main__':
    main()
