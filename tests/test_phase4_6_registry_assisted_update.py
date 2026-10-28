from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'config/registry_watch.json').read_text(encoding='utf-8'))
wf=(ROOT/'.github/workflows/registry-market-validation.yml').read_text(encoding='utf-8')
watch=(ROOT/'scripts/watch_registries.py').read_text(encoding='utf-8')
review=(ROOT/'scripts/build_registry_review.py').read_text(encoding='utf-8')
legal=json.loads((ROOT/'data/mock/legal/documents.json').read_text(encoding='utf-8'))
infra=json.loads((ROOT/'data/mock/infrastructure/schedules.json').read_text(encoding='utf-8'))

assert cfg['mode']=='assisted-registry-watch-v1'
assert cfg['auto_publish'] is False
assert set(cfg['modules'])=={'legal','infrastructure'}
assert cfg['modules']['legal']['canonical_path']=='data/mock/legal/documents.json'
assert cfg['modules']['infrastructure']['canonical_path']=='data/mock/infrastructure/schedules.json'
assert all(x.get('official_url','').startswith('https://vanban.chinhphu.vn/') for x in legal['data'])
assert all(x.get('source_url','').startswith('https://') for x in infra['data'])
assert 'changed_since_previous_check' in watch
assert 'new_since_previous_check' in watch
assert 'auto_publish' in review
assert 'never overwritten' in review
# The Legal/Infrastructure registry watcher is still read-only.
# A separate push-only job may publish a derived Market coverage QA snapshot;
# it must never have permission or logic to mutate Legal/Infrastructure registries.
assert '\npermissions:\n  contents: read\n' in wf
watch_job=wf.split('\n  watch:\n',1)[1].split('\n  publish-market-coverage:\n',1)[0]
assert 'contents: write' not in watch_job
coverage_job=wf.split('\n  publish-market-coverage:\n',1)[1]
assert "if: github.event_name == 'push'" in coverage_job
assert 'contents: write' in coverage_job
assert 'git add data/state/market-coverage.json' in coverage_job
assert 'git add data/mock/legal/' not in coverage_job
assert 'git add data/mock/infrastructure/' not in coverage_job
assert 'actions/cache@v6' in wf
assert 'registry-review-' in wf
assert 'python scripts/watch_registries.py' in wf
assert 'python scripts/build_registry_review.py' in wf
print('Phase 4.6 assisted registry update tests PASS')
