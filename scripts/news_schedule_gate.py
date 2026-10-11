"""Skip a scheduled RSS recovery run if its primary time slot was collected."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP = "50 0,2,4,6,8,10,12,14 * * *"
HOURS = (0, 2, 4, 6, 8, 10, 12, 14)


def parse_time(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def expected_slot(now):
    now = now.astimezone(timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return max(midnight + timedelta(days=d, hours=h, minutes=20)
               for d in (-1, 0) for h in HOURS
               if midnight + timedelta(days=d, hours=h, minutes=20) <= now)


def should_run(event, cron, checked, now):
    if event != "schedule" or cron != BACKUP:
        return True
    return checked is None or checked < expected_slot(now)


def main():
    path = ROOT / "data/state/news-ingestion-health.json"
    snapshot = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    checked = parse_time(snapshot.get("checked_at"))
    now = datetime.now(timezone.utc)
    run = should_run(os.getenv("NEWS_EVENT", ""), os.getenv("NEWS_CRON", ""), checked, now)
    print(f"RSS catch-up gate: run={run}, last_checked={checked}, slot={expected_slot(now)}")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"run={str(run).lower()}\n")


if __name__ == "__main__":
    main()
