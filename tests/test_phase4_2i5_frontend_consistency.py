from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    'usd-vnd-central-rate': {'view': 'fx', 'home': True, 'evidence': 'corroborated', 'unit': 'vnd-per-usd'},
    'sjc-gold-buy': {'view': 'gold', 'home': False, 'evidence': 'corroborated', 'unit': 'vnd-per-tael'},
    'sjc-gold-sell': {'view': 'gold', 'home': True, 'evidence': 'corroborated', 'unit': 'vnd-per-tael'},
    'credit-growth-ytd': {'view': 'liquidity', 'home': True, 'evidence': 'verified', 'unit': 'percent'},
    'bank-funding-growth-ytd': {'view': 'liquidity', 'home': True, 'evidence': 'verified', 'unit': 'percent'},
    'cpi-yoy': {'view': 'inflation', 'home': True, 'evidence': 'verified', 'unit': 'percent'},
    'cpi-mom': {'view': 'inflation', 'home': False, 'evidence': 'verified', 'unit': 'percent'},
    'core-cpi-yoy': {'view': 'inflation', 'home': False, 'evidence': 'verified', 'unit': 'percent'},
}


def main():
    processed_path = ROOT / 'data/processed/macro/observations.json'
    processed = json.loads(processed_path.read_text(encoding='utf-8'))
    publish = json.loads((ROOT / 'data/processed/macro/repository-publish.json').read_text(encoding='utf-8'))
    rows = processed['data']

    assert processed['record_count'] == len(rows) and len(rows) >= 8
    assert processed['repository_publish'] is True
    assert processed['production_write'] is True
    assert publish['repository_publish'] is True
    assert publish['final_record_count'] == len(rows)
    assert hashlib.sha256(processed_path.read_bytes()).hexdigest() == publish['observations_sha256']

    by_id = {row['indicator_id']: row for row in rows}
    assert set(EXPECTED).issubset(set(by_id))
    for iid, spec in EXPECTED.items():
        row = by_id[iid]
        assert row['unit'] == spec['unit']
        assert row['evidence_status'] == spec['evidence']
        assert row['observation_status'] == 'final'

    sources = json.loads((ROOT / 'data/mock/core/sources.json').read_text(encoding='utf-8'))['data']
    source_ids = {source['id'] for source in sources}
    for row in rows:
        assert row['source_id'] in source_ids
        for source_id in row.get('corroboration_source_ids', []):
            assert source_id in source_ids

    macro_js = (ROOT / 'assets/js/macro.js').read_text(encoding='utf-8')
    for iid, spec in EXPECTED.items():
        assert f"'{iid}'" in macro_js
        assert f"{spec['view']}:" in macro_js or spec['view'] == 'fx'
    assert 'Latest observation only · no synthetic history is created.' in macro_js
    assert 'const retainedMockRows = mockRows.filter(row =>' in macro_js and '!productionIndicatorIds.has(row.indicator_id)' in macro_js

    home_js = (ROOT / 'assets/js/home.js').read_text(encoding='utf-8')
    for iid, spec in EXPECTED.items():
        if spec['home']:
            assert f"'{iid}'" in home_js
    for literal in ('10.89', '9.78', '5.08', '25643', '143.5'):
        assert literal not in home_js, f'production value {literal} must not be hard-coded in Home frontend'
    assert "grid?.classList.toggle('metric-grid--controlled', production.active);" in home_js
    assert "DataStore.getProcessedMacroObservations()" in home_js
    assert "DataStore.getProcessedMacroPublishMeta()" in home_js
    assert "change_label: 'Latest only'" in home_js

    css = (ROOT / 'assets/css/main.css').read_text(encoding='utf-8')
    assert '.metric-grid--controlled { grid-template-columns: repeat(4, minmax(0, 1fr)); }' in css

    index = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'home.js?v=4.2J3' in index
    assert 'main.css?v=4.2I5' in index
    assert 'localization-dynamic.js?v=4.2J3' in index

    mapping = json.loads((ROOT / 'config/frontend_indicator_map.json').read_text(encoding='utf-8'))
    assert mapping['frontend_baseline'] == 'v7.2.1+4.2J3.2+4.2K1'
    for iid in EXPECTED:
        assert iid in mapping['mappings']

    print('Phase 4.2I.5 production coverage and frontend consistency tests passed')


if __name__ == '__main__':
    main()
