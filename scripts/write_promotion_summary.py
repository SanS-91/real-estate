from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "data/staging/macro-preview"
META = PREVIEW / "preview-meta.json"
CSV = PREVIEW / "promotion-summary.csv"

print("\n# Macro promotion preview")
if not META.exists():
    print("\nNo promotion preview was produced for this run.")
    raise SystemExit(0)

meta = json.loads(META.read_text(encoding="utf-8"))
print(f"\n- Mode: **{meta.get('mode', 'unknown')}**")
print(f"- Production write: **{str(meta.get('production_write')).lower()}**")
print(f"- Source run: **{meta.get('source_run_id') or 'unknown'}**")
print(f"- Canonical preview: **{meta.get('canonical_preview_count', 0)}**")
print(f"- Evidence preview: **{meta.get('evidence_preview_count', 0)}**")
print(f"- Frontend baseline: **{meta.get('frontend_baseline') or 'unknown'}**")

if CSV.exists():
    rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig")))
    if rows:
        print("\n## Promotion decisions")
        print("| Indicator | Readiness | Action | Value | Period | Source | Frontend |")
        print("|---|---|---|---:|---|---|---|")
        for r in rows:
            val = r.get("value") or "—"
            unit = r.get("unit") or ""
            display = f"{val} {unit}".strip()
            print(
                f"| {r.get('indicator_id','')} | {r.get('readiness_status','')} | {r.get('action','')} | "
                f"{display} | {r.get('period','') or '—'} | {r.get('source_id','') or '—'} | "
                f"{r.get('frontend_compatibility','') or '—'} |"
            )
