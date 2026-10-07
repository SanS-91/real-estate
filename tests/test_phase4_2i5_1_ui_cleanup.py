from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def latest_pair(rows, indicator_id):
    matched = sorted(
        [row for row in rows if row.get('indicator_id') == indicator_id],
        key=lambda row: row.get('data_date') or row.get('period') or '',
    )
    return matched[-1], matched[-2]


def main():
    home_payload = json.loads((ROOT / 'data/mock/home/indicators.json').read_text(encoding='utf-8'))
    home = home_payload['data']
    home_by_id = {row['id']: row for row in home}

    # Phase 4.3D removes fabricated Home fallback values. If controlled Macro
    # production cannot load, the cards stay blank instead of reverting to demo data.
    assert home_payload.get('fallback_only') is True
    for key in ['deposit-demo', 'lending-demo', 'usd-vnd-demo', 'gold-demo', 'credit-demo', 'cpi-demo']:
        assert home_by_id[key]['display_value'] == '—'
        assert home_by_id[key]['source'] == 'Unavailable'

    dynamic = (ROOT / 'assets/js/localization-dynamic.js').read_text(encoding='utf-8')
    assert "'Average Lending Rate': 'Lãi suất cho vay bình quân'" in dynamic
    assert "translate: (text, lang = language())" in dynamic

    macro_js = (ROOT / 'assets/js/macro.js').read_text(encoding='utf-8')
    assert 'label: localizedText(ind.name)' in macro_js
    assert "document.addEventListener('app:language-changed'" in macro_js

    index = (ROOT / 'index.html').read_text(encoding='utf-8')
    macro_html = (ROOT / 'macro.html').read_text(encoding='utf-8')
    assert 'home.js?v=4.3D' in index
    assert 'localization-dynamic.js?v=4.3E' in index
    assert 'macro.js?v=4.2K4' in macro_html
    assert 'localization-dynamic.js?v=4.3E' in macro_html
    assert 'ui=4.2J3.2' in macro_html

    mapping = json.loads((ROOT / 'config/frontend_indicator_map.json').read_text(encoding='utf-8'))
    assert mapping['frontend_baseline'] == 'v7.2.1+4.2J3.2+4.2K4'

    # Home sync must not alter controlled production observations.
    processed = json.loads((ROOT / 'data/processed/macro/observations.json').read_text(encoding='utf-8'))
    assert processed['record_count'] == 15

    print('Phase 4.2I.5.1 UI consistency cleanup tests passed')


if __name__ == '__main__':
    main()
