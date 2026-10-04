from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'candidate'
        cp = subprocess.run([
            sys.executable, str(ROOT/'scripts/candidate_pipeline.py'),
            '--fixture-mode', '--replace-history', '--output-root', str(out)
        ], cwd=ROOT, capture_output=True, text=True)
        if cp.returncode != 0:
            print(cp.stdout); print(cp.stderr); raise SystemExit(cp.returncode)
        obs = json.loads((out/'observations.json').read_text(encoding='utf-8'))
        rep = json.loads((out/'run-report.json').read_text(encoding='utf-8'))
        ready = json.loads((out/'publish-readiness.json').read_text(encoding='utf-8'))
        assert obs['candidate_only'] is True
        assert obs['record_count'] >= 6
        assert rep['production_publish'] is False
        assert rep['status'] == 'pass'
        states = {x['indicator_id']: x['status'] for x in ready['data']}
        assert states['cpi-yoy'] == 'ready'
        assert states['usd-vnd-central-rate'] == 'ready'
        assert states['sjc-gold-bar-sell'] == 'ready'
    print('Candidate pipeline fixture E2E passed')

if __name__ == '__main__': main()
