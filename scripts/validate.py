from __future__ import annotations
from pathlib import Path
import argparse
import json
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def validate_file(data_path: Path, schema_path: Path):
    data = json.loads(data_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    v = Draft202012Validator(schema, format_checker=FormatChecker())
    errs = []
    for i, item in enumerate(data.get("data", [])):
        for e in v.iter_errors(item):
            errs.append(f"{data_path.name} row {i}: {e.message}")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-dir", default=str(ROOT / "data/candidate/macro"))
    args = ap.parse_args()
    c = Path(args.candidate_dir)
    errors = []
    errors += validate_file(c / "observations.json", ROOT / "schemas/macro_observation.schema.json")
    errors += validate_file(c / "research-evidence.json", ROOT / "schemas/research_evidence.schema.json")
    report = json.loads((c / "run-report.json").read_text(encoding="utf-8")) if (c / "run-report.json").exists() else {}
    if report.get("production_publish") is not False:
        errors.append("run-report production_publish must be false")
    if errors:
        print("\n".join(errors)); raise SystemExit(1)
    print("Validation OK")

if __name__ == "__main__":
    main()
