"""Market pricing supplementary references stay compact, separated and recoverable."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/"assets/js/market.js").read_text(encoding="utf-8")
css=(ROOT/"assets/css/market-listing-evidence.css").read_text(encoding="utf-8")
html=(ROOT/"market.html").read_text(encoding="utf-8")
paths=(
    ROOT/"data/mock/market/alternative-price-evidence.json",
    ROOT/"data/mock/market/secondary-listing-evidence.json",
    ROOT/"data/mock/market/alternative-subproject-monthly-evidence.json")
rows=sum((json.loads(p.read_text(encoding="utf-8"))["data"] for p in paths), [])
def kind(row):
    if row["metric_type"]=="historical-launch-starting-price-per-sqm" or str(row.get("publisher_claim_status","")).startswith("expired"):
        return "historical"
    if row["metric_type"]=="popular-asking-price-per-sqm":
        return "popular"
    return "listing"

assert len(rows)==10
assert {x:sum(kind(row)==x for row in rows) for x in ("popular","listing","historical")}=={
    "popular":4,"listing":3,"historical":3}
assert len({row["project_id"] for row in rows})==7
assert sum(row["project_id"]=="vinhomes-grand-park" for row in rows)==4
assert "function alternativePriceCardsHTML(projectIds, options = {})" in js
assert "<details class=\"market-price-references\" " in js
assert "options.expanded ? 'open' : ''" in js
assert "Giá tham khảo bổ sung" in js
assert "Giá phổ biến theo nguồn" in js
assert "Giá rao của từng căn" in js
assert "Giá lịch sử" in js
assert "market-evidence-group--historical" in js
assert "class=\"market-evidence-row\"" in js
assert "Ghi chú phương pháp đầy đủ" in js
assert "sourceRef(row.source_id" in js
assert "data.oneHousingSubprojectEvidence" in js
assert "Giá từ kỳ lịch sử, không sử dụng như giá hiện tại." in js
assert "HTTP 403" in js
assert "market-price-references__summary:focus-visible" in css
assert "max-width:700px" in css
assert "grid-template-areas:" in css
assert "prefers-reduced-motion" in css
assert "market-listing-evidence.css?v=" in html
assert "market.js?v=" in html
assert "getAlternativePriceEvidence()" in js and "getSecondaryListingEvidence()" in js and "getOneHousingSubprojectEvidence()" in js
assert json.loads((ROOT/"data/mock/market/listing-observations.json").read_text(encoding="utf-8"))["record_count"]==18
print("PASS: 10 source records in 3 evidence groups, compact keyboard-accessible mobile UI; source detail preserved, aggregate price history unchanged.")
