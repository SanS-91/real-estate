"""Phase 8A: check, publication and observation are distinct, and UI states agree."""
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("health", ROOT / "scripts/build_data_health.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

matrix = {x["id"]: x for x in json.loads((ROOT / "config/update_matrix.json").read_text(encoding="utf-8"))["datasets"]}
actual = json.loads((ROOT / "data/processed/macro/observations.json").read_text(encoding="utf-8"))
now = datetime.now(timezone.utc)

daily = mod.prod_info({"id": "macro-daily-markets"}, matrix, now)
rows = [x for x in actual["data"] if x.get("indicator_id") in matrix["macro-daily-markets"]["indicator_ids"]]
promoted = [datetime.fromisoformat(x["promoted_at"].replace("Z", "+00:00")) for x in rows if x.get("promoted_at")]
assert rows and promoted
assert daily["last_data_change_at"] == max(promoted).isoformat()
assert daily["last_production_at"] == actual["generated_at"]
assert daily["latest_source_period"] == max(x["period"] for x in rows if x.get("period"))
assert daily["record_count"] == len(rows)

m2 = mod.prod_info({"id": "macro-m2-ytd"}, matrix, now)
if m2["record_count"] == 0:
    assert m2["last_data_change_at"] is None, "Rewritten production file is not a new M2 observation"
assert m2["release_status"] in {"missing-release", "current", "awaiting-first"}

maint = (ROOT / "assets/js/maintenance.js").read_text(encoding="utf-8")
home = (ROOT / "assets/js/home.js").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/unified-data-health.yml").read_text(encoding="utf-8")
assert "async function buildLegacyModel()" in maint
assert "async function buildModel()" in maint
assert "DataStore.getDataHealth()" in maint and "DataStore.getDataHealth()" in home
assert "last_data_change_at || entry.last_production_at" in maint
assert "source_freshness === 'release-missing'" in maint
assert "(model.counts.degraded || 0)" in maint
assert "git reset --hard origin/main" in workflow
assert "git rebase origin/main" not in workflow
assert "python scripts/build_data_health.py --output data/state/data-health.json" in workflow
print("PASS Phase 8A unified health, record-change semantics and conflict-safe publish")
