from pathlib import Path
import importlib.util, json

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("legal_collector",ROOT/"scripts/legal_candidate_collector.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

html=(ROOT/"tests/fixtures/legal_official_document_sample.html").read_text(encoding="utf-8")
row=mod.parse(html,"https://vanban.chinhphu.vn/?docid=fixture&pageid=27160","2026-10-08T00:00:00Z")

assert row["document_number"]=="200/2026/NĐ-CP"
assert row["document_type"]=="decree"
assert row["issued_date"]=="2026-10-05"
assert row["effective_date"]=="2026-10-05"
assert row["agency_ids"]==["government"]
assert "land" in row["topic_ids"]
assert "investment" in row["topic_ids"]
assert row["primary_source_id"]=="gov-vietnam-legal-documents"
assert row["collector_provenance"]["review_required"] is True
assert mod.validate(row)==[]

canonical=json.loads((ROOT/"data/mock/legal/documents.json").read_text(encoding="utf-8"))["data"]
existing=canonical[0]
assert existing["document_number"]
assert mod.identity(existing)[0]==existing["document_number"].upper()

print("Phase 5.7A legal candidate collector tests PASS")
