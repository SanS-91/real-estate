"""Test strict dealer-only scraping; page-text changes cannot become approved FS data."""
import importlib.util
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("candidates",ROOT/"scripts/market_dealer_commercial_candidates.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
prices="""<html><body><h1>Izumi Canaria tháng 10/2026</h1><table>
<tr><th>Loại sản phẩm</th><th>Diện tích đất / sàn</th><th>Giá niêm yết từ</th></tr>
<tr><td>Nhà phố vườn zone 1</td><td>114–164 m² / 141–190 m²</td><td>8,55 tỷ đồng</td></tr>
<tr><td>Nhà phố vườn zone 2</td><td>114 m² / 152–157 m²</td><td>9,18 tỷ đồng</td></tr>
<tr><td>Nhà phố vườn zone 3</td><td>114 m² / 153–157 m²</td><td>9,52 tỷ đồng</td></tr>
<tr><td>Biệt thự song lập</td><td>234–322 m²</td><td>16,4 tỷ đồng</td></tr>
</table><p>Ví dụ giá sau ưu đãi 7,73 tỷ - không lấy ví dụ này.</p></body></html>"""
policy="""<html><body><h1>Izumi Canaria TB153</h1><p>Cập nhật 27/10/2026:
Thông báo TB153 ngày 02/10/2026 đã thay hoàn toàn TB143, áp dụng 05/10 tới 31/12/2026.</p></body></html>"""
def fetch(url):
    return SimpleNamespace(status_code=200,url=url,text=policy if url==m.POLICY_URL else prices)
stamp=datetime(2026,10,28,12,0,tzinfo=timezone.utc)
out=m.build(stamp,fetch)
assert out["completeness"]=="reviewable-full-table"
assert out["price_table_records_recognized"]==4
assert {(x["zone"],x["reported_start_price_vnd"]) for x in out["price_candidates"]}=={
    ("Zone 1",8550000000),("Zone 2",9180000000),("Zone 3",9520000000),(None,16400000000)}
assert out["policy_candidate"]["supersession_detected"] is True
assert out["policy_candidate"]["signed_document_verified"] is False
assert out["auto_promoted_prices"]==0 and out["approved_payment_schemes"]==0
assert out["net_price_pv_published"] is False
assert all(x["eligible_for_pv"] is False and x["eligible_for_net_price"] is False
           and x["eligible_for_fs_asp"] is False for x in out["price_candidates"])
assert all("land_area_sqm" not in x for x in out["price_candidates"])
# A source may render its quotation as cards/paragraphs, not a semantic table.
paragraphs="""<html><body><h2>Giá niêm yết theo bảng tính tháng 10/2026</h2>
<p>Nhà phố vườn zone 1: 114 m², giá từ 8,55 tỷ đồng</p>
<p>Nhà phố vườn zone 2: 114 m², giá từ 9,18 tỷ đồng</p>
<p>Nhà phố vườn zone 3: 114 m², giá từ 9,52 tỷ đồng</p>
<p>Biệt thự song lập: 234 m², giá từ 16,4 tỷ đồng</p>
<h2>Ví dụ giá sau ưu đãi</h2><p>zone 3 còn khoảng 7,73 tỷ</p></body></html>"""
paragraph_rows=m.extract_price_rows(paragraphs)
assert len(paragraph_rows)==4,paragraph_rows
assert {(x["zone"],x["reported_start_price_vnd"]) for x in paragraph_rows}=={
    ("Zone 1",8550000000),("Zone 2",9180000000),("Zone 3",9520000000),(None,16400000000)}
# Ad text or a new paragraph may mention an amount, but only source product rows count.
bad="<html><body><div>Nhà phố vườn zone 1 2 tỷ</div><p>7,73 tỷ sau ưu đãi</p></body></html>"
assert not m.extract_price_rows(bad)
# Partial or inaccessible pages must fail closed.
def blocked(url):return SimpleNamespace(status_code=403,url=url,text="blocked")
unavailable=m.build(stamp,blocked)
assert unavailable["completeness"]=="partial-or-unavailable"
assert unavailable["price_candidates"]==[]
assert unavailable["policy_candidate"] is None
assert unavailable["auto_promoted_prices"]==0
print("PASS daily dealer source candidates: isolated category table, TB153 alert, no FS price/PV promotion")
