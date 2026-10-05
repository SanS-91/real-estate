from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/macro-candidate-6"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    with tempfile.TemporaryDirectory() as td:
        # Output must still be under repo data/staging due hard safety. Use a unique repo-local path.
        out = ROOT / "data/staging/test-macro-preview"
        shutil.rmtree(out, ignore_errors=True)
        subprocess.run([
            sys.executable, str(ROOT / "scripts/promotion_preview.py"),
            "--candidate-dir", str(FIXTURE),
            "--output-dir", str(out),
        ], check=True, stdout=subprocess.DEVNULL)

        canon = load(out / "canonical-observations.preview.json")
        evidence = load(out / "evidence-observations.preview.json")
        manifest = load(out / "promotion-manifest.json")
        meta = load(out / "preview-meta.json")

        assert canon["preview_only"] is True
        assert evidence["preview_only"] is True
        assert meta["production_write"] is False
        assert canon["record_count"] == 3, canon["record_count"]
        assert evidence["record_count"] == 3, evidence["record_count"]
        assert {x["indicator_id"] for x in canon["data"]} == {"cpi-yoy", "cpi-mom", "core-cpi-yoy"}
        assert {x["indicator_id"] for x in evidence["data"]} == {"usd-vnd-central-rate", "sjc-gold-buy", "sjc-gold-sell"}
        assert all(x["evidence_status"] == "verified" for x in canon["data"])
        assert all(x["evidence_status"] == "reported" for x in evidence["data"])
        actions = {x["indicator_id"]: x["action"] for x in manifest["data"]}
        assert actions["cpi-yoy"] == "promote-canonical-preview"
        assert actions["usd-vnd-central-rate"] == "hold-evidence"
        compat = {x["indicator_id"]: x["frontend_compatibility"] for x in manifest["data"]}
        assert compat["sjc-gold-buy"] == "compatible"
        assert compat["sjc-gold-sell"] == "compatible"
        shutil.rmtree(out, ignore_errors=True)

        # Ensure production path is explicitly rejected.
        p = subprocess.run([
            sys.executable, str(ROOT / "scripts/promotion_preview.py"),
            "--candidate-dir", str(FIXTURE),
            "--output-dir", str(ROOT / "data/processed/macro"),
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert p.returncode != 0
        assert "cannot write to data/processed" in p.stdout

    print("promotion preview tests: PASS")


if __name__ == "__main__":
    main()
