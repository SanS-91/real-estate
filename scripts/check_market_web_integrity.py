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
        assert parsed.scheme == "https"
        assert date(2024, 1, 1) <= date.fromisoformat(item["source_date"]) <= date.today()
        assert item["data_basis"] and item["not_equivalent_to"]
        assert "sales_units" not in item and "new_supply" not in item
        assert item["region_ids"] and item["segment_ids"]
        if item["data_basis"] == "press-attributed-secondary-confirmation-only":
            urls = item.get("supporting_source_urls", [])
            hosts = {(urlsplit(link).hostname or "").lower().removeprefix("www.") for link in urls
                     if urlsplit(link).scheme == "https"}
            assert len(hosts) >= 2 and (parsed.hostname or "").lower().removeprefix("www.") in hosts
            publisher = urlsplit(item.get("publisher_report_url", ""))
            assert publisher.scheme == "https" and (publisher.hostname or "").endswith(".savills.com.vn")
            assert item.get("verification_status") == "secondary-corroborated-not-publisher-table-verified"
            metrics = item["reported_indicators"]
            assert metrics["new_launches_units_approx"] > 0
            assert metrics["transactions_units_approx"] > 0
            assert 0 < metrics["market_absorption_rate_approx"] < 1
            assert metrics["primary_stock_units_approx"] > metrics["new_launches_units_approx"]
        else:
            assert (parsed.hostname or "").endswith(".savills.com.vn")
            assert "reported_indicators" not in item

    listings = json.loads(read("data/mock/market/listing-observations.json"))
    assert listings["record_count"] == len(listings["data"])
    print(f"Market integrity PASS: {len(briefs['data'])} briefs, "
          f"{sum(x.get('status') == 'reviewed' for x in listings['data'])} reviewed listing snapshots")


if __name__ == "__main__":
    check()
