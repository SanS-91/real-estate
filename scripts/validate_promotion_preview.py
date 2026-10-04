from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    "canonical-observations.preview.json",
    "evidence-observations.preview.json",
    "promotion-manifest.json",
    "preview-meta.json",
    "promotion-summary.csv",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview-dir", default="data/staging/macro-preview")
    args = ap.parse_args()
    p = Path(args.preview_dir)
    if not p.is_absolute():
        p = ROOT / p
    p = p.resolve()

    staging_root = (ROOT / "data/staging").resolve()
    processed_root = (ROOT / "data/processed").resolve()
    if processed_root == p or processed_root in p.parents:
        raise SystemExit("Safety violation: preview validation cannot target data/processed")
    if staging_root != p and staging_root not in p.parents:
        raise SystemExit(f"Safety violation: preview dir must remain under {staging_root}")

    missing = [name for name in EXPECTED if not (p / name).exists()]
    if missing:
        raise SystemExit("Missing promotion preview files: " + ", ".join(missing))

    canon = load_json(p / "canonical-observations.preview.json")
    evidence = load_json(p / "evidence-observations.preview.json")
    manifest = load_json(p / "promotion-manifest.json")
    meta = load_json(p / "preview-meta.json")

    errors = []
    if meta.get("production_write") is not False:
        errors.append("preview-meta production_write must be false")
    if meta.get("mode") != "dry-run-promotion-preview":
        errors.append("preview-meta mode must be dry-run-promotion-preview")
    for label, payload in [("canonical", canon), ("evidence", evidence)]:
        if payload.get("preview_only") is not True:
            errors.append(f"{label} payload preview_only must be true")
        data = payload.get("data")
        if not isinstance(data, list):
            errors.append(f"{label} data must be a list")
            continue
        if payload.get("record_count") != len(data):
            errors.append(f"{label} record_count mismatch")
        if any(x.get("preview_only") is not True for x in data):
            errors.append(f"{label} contains non-preview record")

    if manifest.get("production_write") is not False:
        errors.append("promotion-manifest production_write must be false")
    if not isinstance(manifest.get("data"), list):
        errors.append("promotion-manifest data must be a list")

    canonical_ids = {x.get("id") for x in canon.get("data", [])}
    evidence_ids = {x.get("id") for x in evidence.get("data", [])}
    overlap = sorted(x for x in canonical_ids & evidence_ids if x)
    if overlap:
        errors.append("records appear in both canonical and evidence preview: " + ", ".join(overlap))

    if errors:
        print("Promotion preview validation: FAIL", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        raise SystemExit(1)

    print("Promotion preview validation: PASS")
    print(f"Canonical preview: {canon.get('record_count', 0)}")
    print(f"Evidence preview: {evidence.get('record_count', 0)}")
    print("Production write: false")


if __name__ == "__main__":
    main()
