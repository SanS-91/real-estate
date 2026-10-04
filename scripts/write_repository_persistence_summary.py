from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data/staging/repository-persistence/persistence-run.json"

print("## Macro repository persistence")
print()
if not REPORT.exists():
    print("No repository persistence report was produced for this run.")
    raise SystemExit(0)

r = json.loads(REPORT.read_text(encoding="utf-8"))
print(f"- Status: **{r.get('status')}**")
print(f"- Source collector run: **#{r.get('source_run_number')}**")
print(f"- Source artifact: `{r.get('source_artifact')}`")
print(f"- Repository write prepared: **{str(r.get('repository_write')).lower()}**")
print(f"- Frontend publish: **{str(r.get('frontend_publish')).lower()}**")
print(f"- Prior records: **{r.get('prior_record_count')}**")
print(f"- Added records: **{r.get('added_record_count')}**")
print(f"- Final records: **{r.get('final_record_count')}**")
if r.get("added"):
    print()
    print("### Added canonical records")
    print()
    print("| Indicator | Period | Value | Unit | Source |")
    print("|---|---|---:|---|---|")
    for x in r["added"]:
        print(f"| {x.get('indicator_id')} | {x.get('period')} | {x.get('value')} | {x.get('unit')} | {x.get('source_id')} |")
print()
print("Repository persistence is a manual gate. This phase does not connect the frontend to processed data.")
