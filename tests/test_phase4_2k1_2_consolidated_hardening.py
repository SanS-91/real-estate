from pathlib import Path
import json, subprocess, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/"candidate"
        cp=subprocess.run([
            sys.executable, str(ROOT/"scripts/candidate_pipeline.py"),
            "--fixture-mode", "--replace-history", "--output-root", str(out),
            "--source", "vietnamplus-policy-rates",
            "--source", "banking-times-policy-rates",
            "--source", "vietnamplus-interbank-rates",
        ], cwd=ROOT, capture_output=True, text=True)
        if cp.returncode != 0:
            print(cp.stdout); print(cp.stderr); raise SystemExit(cp.returncode)
        report=json.loads((out/"run-report.json").read_text(encoding="utf-8"))
        health=json.loads((out/"source-health.json").read_text(encoding="utf-8"))
        obs=json.loads((out/"observations.json").read_text(encoding="utf-8"))
        assert set(report["selected_sources"]) == {"vietnamplus-policy-rates","banking-times-policy-rates","vietnamplus-interbank-rates"}
        assert report["new_observations"] == 7
        assert {x["source"] for x in health["sources"]} == {"vietnamplus-policy-rates","banking-times-policy-rates","vietnamplus-interbank-rates"}
        assert health["healthy"] == 3
        ids={x["indicator_id"] for x in obs["data"]}
        assert {"policy-refinancing-rate","policy-rediscount-rate","policy-overnight-lending-rate","interbank-on"}.issubset(ids)
    print("Phase 4.2K.1.2 consolidated fallback hardening tests passed")

if __name__=="__main__": main()
