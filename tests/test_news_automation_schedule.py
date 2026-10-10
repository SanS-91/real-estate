from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json, re

ROOT = Path(__file__).resolve().parents[1]
config = json.loads((ROOT / 'config/news-automation.json').read_text(encoding='utf-8'))
workflow = (ROOT / '.github/workflows/market-news-rss.yml').read_text(encoding='utf-8')
found = re.search(r"cron: '([^']+)'", workflow)
assert found, "Missing scheduled GitHub Actions news cron"
assert config['utc_cron'] == found.group(1), "Published monitoring schedule must equal actual Actions schedule"
minute, hours_expr, day, month, dow = found.group(1).split()
assert (day, month, dow) == ('*', '*', '*')
assert int(minute) == config['utc_minute'] == 20
hours = [int(hour) for hour in hours_expr.split(',')]
assert hours == config['utc_hours'] == [0,2,4,6,8,10,12,14]
local = [datetime(2026,10,10,h,int(minute),tzinfo=timezone.utc)
          .astimezone(ZoneInfo(config['timezone'])).strftime('%H:%M') for h in hours]
assert local == config['local_times'] == ['07:20','09:20','11:20','13:20','15:20','17:20','19:20','21:20']
assert config['max_delay_minutes'] >= 30
assert 'cancel-in-progress: false' in workflow, "Do not cancel news collection in progress"
assert 'data/state/news-ingestion-health.json' in workflow
assert 'mode promote' in workflow
print('PASS news cron: exactly eight daily VN time checks, source monitoring and no cancellation')
