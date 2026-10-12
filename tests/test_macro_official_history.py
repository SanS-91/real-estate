#!/usr/bin/env python3
"""Validate manually source-reviewed NSO monthly history without weakening live publication gates."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / 'data/processed/macro/historical-observations.json'
CURRENT = ROOT / 'data/processed/macro/observations.json'

EXPECTED = {
    'cpi-yoy': [2.53, 3.35, 4.65, 5.46, 5.60, 4.69, 4.45, 4.89],
    'cpi-mom': [0.05, 1.14, 1.23, 0.84, 0.29, -0.39, -0.12, 0.47],
    'core-cpi-yoy': [3.19, 3.74, 3.96, 4.66, 4.67, 4.50, None, None],
}

def validate():
    p = json.loads(HISTORY.read_text(encoding='utf-8'))
    live = json.loads(CURRENT.read_text(encoding='utf-8'))
    assert p['schema_version'] == 1
    assert p['mode'] == 'verified-official-nso-history-v1'
    assert p['repository_publish'] is True and p['frontend_publish'] is False
    assert p['record_count'] == len(p['data']) == 22
    assert live['record_count'] == len(live['data'])
    live_keys = {(r['indicator_id'],r['period_type'],r['period']) for r in live['data']}
    seen = set()
    for row in p['data']:
        key = (row.get('indicator_id'),row.get('period_type'),row.get('period'))
        assert key not in seen, ('duplicate historical record', key)
        assert key not in live_keys, ('historical overwrites live production', key)
        seen.add(key)
        assert row['indicator_id'] in EXPECTED
        assert row['period_type'] == 'month' and re.fullmatch(r'2026-0[1-8]', row['period'])
        assert row['unit'] == 'percent'
        assert row['source_id'] == 'nso-vietnam'
        assert urlparse(row['source_url']).scheme == 'https'
        assert urlparse(row['source_url']).hostname == 'www.nso.gov.vn'
        assert row['evidence_status'] == 'verified' and row['observation_status'] == 'final'
        assert row['historical_observation'] is True and row['source_reviewed_at']
        assert row['published_at'] > row['period'] and row['source_url'].startswith('https://www.nso.gov.vn/')
        assert row['source_record_id'] == row['id'] == f"nso-historical-{row['indicator_id']}-{row['period']}"
        assert row['value'] == EXPECTED[row['indicator_id']][int(row['period'][-2:])-1]
    for indicator, values in EXPECTED.items():
        expected = sum(value is not None for value in values)
        assert sum(row['indicator_id'] == indicator for row in p['data']) == expected
    js = (ROOT / 'assets/js/macro.js').read_text(encoding='utf-8')
    store = (ROOT / 'assets/js/data-store.js').read_text(encoding='utf-8')
    html = (ROOT / 'macro.html').read_text(encoding='utf-8')
    assert 'getVerifiedMacroHistory' in store and 'getVerifiedMacroHistory' in js
    assert 'validHistoricalRows' in js and 'currentProductionRows' in js
    assert 'historical-observations.json' in store
    assert '20261012-history1' in html
    assert 'Historical periods' in js or 'historicalCount' in js
    return {'added_history':len(seen),'live_protected':len(live_keys),'source':'nso-vietnam'}

if __name__ == '__main__':
    print(json.dumps(validate(), indent=2))
