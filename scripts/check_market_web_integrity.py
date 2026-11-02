"""Fail-closed checks for public Market assets and research metric separation."""
from __future__ import annotations
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
read = lambda path: (ROOT / path).read_text(encoding="utf-8")


def check():
    html = read("market.html")
    css = read("assets/css/main.css")
    js = read("assets/js/market.js")
    store = read("assets/js/data-store.js")
    assert html.lstrip().lower().startswith("<!doctype html>"), "market.html is not HTML"
    assert "</html>" in html and '<body data-page="market">' in html
    assert css.lstrip().startswith(":root"), "main.css is not CSS"
    assert "<!doctype html>" not in css, "HTML accidentally written to stylesheet"
    assert js.lstrip().startswith("(() => {"), "market.js is not JS"
    assert "DataStore.getMarketResearchBriefs()" in js
    assert "getMarketResearchBriefs:" in store
    assert "item.status === 'reviewed'" in js, "primary asking price must use reviewed observations"
    assert "marketResearchBriefsHTML(region,segment)" in js
    assert "market-research-briefs" in js
    assert "assets/css/main.css?" in html and "assets/js/market.js?" in html

    briefs = json.loads(read("data/mock/market/research-briefs.json"))
    assert briefs["record_count"] == len(briefs["data"])
    ids = set()
    for item in briefs["data"]:
        assert item["id"] not in ids
        ids.add(item["id"])
        assert item["source_id"] == "savills-vietnam-market"
        parsed = urlsplit(item["source_url"])
        assert parsed.scheme == "https" and (parsed.hostname or "").endswith(".savills.com.vn")
        assert date(2024, 1, 1) <= date.fromisoformat(item["source_date"]) <= date.today()
        assert item["data_basis"] and item["not_equivalent_to"]
        assert "sales_units" not in item and "new_supply" not in item
        assert item["region_ids"] and item["segment_ids"]

    listings = json.loads(read("data/mock/market/listing-observations.json"))
    assert listings["record_count"] == len(listings["data"])
    print(f"Market integrity PASS: {len(briefs['data'])} briefs, "
          f"{sum(x.get('status') == 'reviewed' for x in listings['data'])} reviewed listing snapshots")


if __name__ == "__main__":
    check()
