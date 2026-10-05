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
    home = json.loads((ROOT / 'data/mock/home/indicators.json').read_text(encoding='utf-8'))['data']
    home_by_id = {row['id']: row for row in home}
    macro = json.loads((ROOT / 'data/mock/macro/observations.json').read_text(encoding='utf-8'))['data']

    deposit_current, deposit_previous = latest_pair(macro, 'deposit-rate-12m-average')
    lending_current, lending_previous = latest_pair(macro, 'lending-rate-average')

    assert home_by_id['deposit-demo']['display_value'] == f"{deposit_current['value']:.1f}% p.a."
    assert home_by_id['deposit-demo']['change_label'] == f"{deposit_current['value'] - deposit_previous['value']:+.2f} ppt"
    assert home_by_id['lending-demo']['label'] == 'Average Lending Rate'
    assert home_by_id['lending-demo']['display_value'] == f"{lending_current['value']:.1f}% p.a."
    assert home_by_id['lending-demo']['change_label'] == f"{lending_current['value'] - lending_previous['value']:.2f} ppt"

    dynamic = (ROOT / 'assets/js/localization-dynamic.js').read_text(encoding='utf-8')
    assert "'Average Lending Rate': 'Lãi suất cho vay bình quân'" in dynamic
    assert "translate: (text, lang = language())" in dynamic

    macro_js = (ROOT / 'assets/js/macro.js').read_text(encoding='utf-8')
    assert 'label: localizedText(ind.name)' in macro_js
    assert "document.addEventListener('app:language-changed'" in macro_js

    index = (ROOT / 'index.html').read_text(encoding='utf-8')
    macro_html = (ROOT / 'macro.html').read_text(encoding='utf-8')
    assert 'home.js?v=4.2I5.1' in index
    assert 'localization-dynamic.js?v=4.2I5.1' in index
    assert 'macro.js?v=4.2I5.1' in macro_html
    assert 'localization-dynamic.js?v=4.2I5.1' in macro_html
    assert 'ui=4.2I5.1' in macro_html

    mapping = json.loads((ROOT / 'config/frontend_indicator_map.json').read_text(encoding='utf-8'))
    assert mapping['frontend_baseline'] == 'v7.2.1+4.2I5.1'

    # This cleanup must not alter controlled production observations.
    processed = json.loads((ROOT / 'data/processed/macro/observations.json').read_text(encoding='utf-8'))
    assert processed['record_count'] == 8

    print('Phase 4.2I.5.1 UI consistency cleanup tests passed')


if __name__ == '__main__':
    main()
