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
print(f"- Unavailable/degraded sources: **{', '.join(r.get('unavailable_sources',[])) or 'none'}**")
if r.get('unavailable_pools'):
    print(f"- Unavailable indicator pools: **{', '.join(r.get('unavailable_pools', []))}**")
if r.get('pool_coverage'):
    print('\n## Indicator pool coverage')
    print('| Pool | Coverage | Available indicators |')
    print('|---|---|---:|')
    for x in r.get('pool_coverage', []):
        print(f"| {x.get('pool_id','')} | {x.get('coverage_status','')} | {x.get('available_indicator_count',0)}/{x.get('indicator_count',0)} |")
if r.get('gate_errors'):
    print(f"- Gate errors: **{' | '.join(r.get('gate_errors', []))}**")
if health_path.exists():
    h=json.loads(health_path.read_text(encoding='utf-8'))
    print('\n## Source health')
    print('| Source | Status | Records | Final URL |')
    print('|---|---|---:|---|')
    for x in h.get('sources',[]):
        url=x.get('final_url') or x.get('target_url') or ''
        print(f"| {x.get('source','')} | {x.get('status','')} | {x.get('records',0)} | {url} |")
    errors=[x for x in h.get('sources',[]) if x.get('error')]
    if errors:
        print('\n## Source errors')
        for x in errors:
            print(f"- **{x.get('source')}**: {x.get('error')}")
