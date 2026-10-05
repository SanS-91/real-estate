from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/processed/macro"

if not (DIR / "promotion-run.json").exists():
    print("## Controlled production promotion\n\nSkipped for this run. No production files were created.")
    raise SystemExit(0)

r = json.loads((DIR / "promotion-run.json").read_text(encoding="utf-8"))
print("## Controlled production promotion")
print()
print(f"- Mode: `{r.get('mode')}`")
print(f"- Source run: `{r.get('source_run_id')}`")
print(f"- Prior records: **{r.get('prior_record_count', 0)}**")
print(f"- Added: **{r.get('added_record_count', 0)}**")
print(f"- Unchanged: **{r.get('unchanged_record_count', 0)}**")
print(f"- Held by controlled policy: **{r.get('held_record_count', 0)}**")
print(f"- Conflicts: **{r.get('conflict_count', 0)}**")
print(f"- Final production records: **{r.get('final_record_count', 0)}**")
print("- Repository publish: **false**")
print("- Frontend publish: **false**")
print()
if r.get("added"):
    print("### Added canonical records")
    print("| Indicator | Period | Value | Unit | Source |")
    print("|---|---:|---:|---|---|")
    for x in r["added"]:
        print(f"| {x.get('indicator_id')} | {x.get('period')} | {x.get('value')} | {x.get('unit')} | {x.get('source_id')} |")
    print()
if r.get("held"):
    print("### Held by controlled production policy")
    print("| Indicator | Period | Action | Reason |")
    print("|---|---:|---|---|")
    for x in r["held"]:
        print(f"| {x.get('indicator_id')} | {x.get('period')} | {x.get('action')} | {x.get('reason')} |")
