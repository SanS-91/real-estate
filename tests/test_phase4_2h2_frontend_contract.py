from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    indicators = json.loads((ROOT/'data/mock/macro/indicators.json').read_text(encoding='utf-8'))['data']
    ids = {x['id'] for x in indicators}
    assert {'usd-vnd-central-rate','sjc-gold-buy','sjc-gold-sell'} <= ids

    sources = json.loads((ROOT/'data/mock/core/sources.json').read_text(encoding='utf-8'))['data']
    source_ids = {x['id'] for x in sources}
    assert {'nso-vietnam','vna-vietnamplus','banking-times-vn','baonghean-gold','vietnamnet-gold'} <= source_ids

    js = (ROOT/'assets/js/macro.js').read_text(encoding='utf-8')
    for token in ["'usd-vnd-central-rate'", "'sjc-gold-buy'", "'sjc-gold-sell'", "evidenceStatus: 'corroborated'"]:
        assert token in js, token

    mapping = json.loads((ROOT/'config/frontend_indicator_map.json').read_text(encoding='utf-8'))['mappings']
    assert mapping['sjc-gold-buy']['status'] == 'compatible'
    assert mapping['sjc-gold-sell']['status'] == 'compatible'
    assert mapping['usd-vnd-central-rate']['status'] == 'compatible'

    print('Phase 4.2H.2 frontend contract tests passed')

if __name__ == '__main__':
    main()
