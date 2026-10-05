from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from collectors.vietnamplus_central_rate import (
    discover_vietnamplus_central_rate_url,
    parse_vietnamplus_central_rate,
)


def main():
    cfg = json.loads((ROOT / 'config/live_sources.json').read_text(encoding='utf-8'))
    src = next(x for x in cfg['sources'] if x['key'] == 'vietnamplus-central-rate')
    assert src['landing_url'] == 'https://en.vietnamplus.vn/state-bank-of-vietnam-tag62.vnp', src

    listing = (ROOT / 'tests/fixtures/vietnamplus_central_rate_listing_sample.html').read_text(encoding='utf-8')
    url = discover_vietnamplus_central_rate_url(listing, src['landing_url'])
    assert url.endswith('/reference-exchange-rate-up-7-vnd-at-weeks-begining-post353066.vnp'), url

    # Current Oct-5 article shape: parser must recover both latest date and 25,643 rate.
    detail = """
    <html><head><meta property='article:published_time' content='2026-10-05T09:08:00+07:00'></head>
    <body>
      <h1>Reference exchange rate up 7 VND at week’s begining</h1>
      <p>The State Bank of Vietnam set the daily reference exchange rate at 25,643 VND/USD on October 5,
      up 7 VND from the last working day of the previous week.</p>
    </body></html>
    """
    rows = parse_vietnamplus_central_rate(detail, url, '2026-10-05T03:50:00+00:00')
    assert len(rows) == 1, rows
    assert rows[0]['value'] == 25643, rows[0]
    assert rows[0]['period'] == '2026-10-05', rows[0]
    assert rows[0]['source_id'] == 'vna-vietnamplus', rows[0]

    # If no listing date is available, keep deterministic DOM-order fallback rather than fail discovery.
    undated = '''
      <a href="/reference-exchange-rate-old-post1.vnp">Reference exchange rate rises</a>
      <a href="/reference-exchange-rate-new-post2.vnp">Reference exchange rate falls</a>
    '''
    fallback = discover_vietnamplus_central_rate_url(undated, src['landing_url'])
    assert fallback.endswith('/reference-exchange-rate-old-post1.vnp'), fallback

    print('Phase 4.2H.4 VietnamPlus latest-discovery tests passed')


if __name__ == '__main__':
    main()
