from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]
report_path = ROOT/'data/candidate/macro/run-report.json'
health_path = ROOT/'data/candidate/macro/source-health.json'
print('# Macro candidate collector')
if not report_path.exists():
    print('\nNo current run report was produced. Check rejected output/logs.')
    raise SystemExit(0)
r = json.loads(report_path.read_text(encoding='utf-8'))
print(f"\n- Status: **{r.get('status','unknown')}**")
print(f"- Candidate only: **yes**")
print(f"- Production publish: **{str(r.get('production_publish')).lower()}**")
print(f"- New observations: **{r.get('new_observations',0)}**")
print(f"- Candidate observations total: **{r.get('candidate_observations_total',0)}**")
print(f"- Hard source failures: **{', '.join(r.get('hard_source_failures',[])) or 'none'}**")
if health_path.exists():
    h=json.loads(health_path.read_text(encoding='utf-8'))
    print('\n## Source health')
    print('| Source | Status | Records | Final URL |')
    print('|---|---|---:|---|')
    for x in h.get('sources',[]):
        url=x.get('final_url') or x.get('target_url') or ''
        print(f"| {x.get('source','')} | {x.get('status','')} | {x.get('records',0)} | {url} |")
