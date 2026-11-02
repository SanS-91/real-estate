"""Regression tests for source-dated individual landed asking offers."""
import io
import sys
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from market_landed_unit_listings import (
    parse_detail, discover, site_url, evaluate, run, fingerprint
)

NOW=datetime(2026,11,2,8,0,tzinfo=timezone.utc)
URL="https://www.nhatot.com/mua-ban-nha-dat-thanh-pho-bien-hoa-dong-nai/134089812.htm"
INDEX="https://www.nhatot.com/mua-ban-du-an-izumi-city-thanh-pho-bien-hoa-pj655547752"
PROJECT={"id":"izumi-city","name":"Izumi City","segment_ids":["landed"]}
HTML="""<html><head><meta property="article:modified_time" content="2026-11-01T08:01:00+07:00"></head>
<body><main><h1>Mua nhà phố Izumi City chỉ đóng 4,8 tỷ lúc nhận nhà</h1>
<div>4 PN • Nhà phố liền kề 7,6 tỷ 66,67 triệu/m² 114 m² Cập nhật 1 ngày trước</div>
<section><h2>Đặc điểm bất động sản</h2><p>Loại hình Nhà phố liền kề</p>
<p>Diện tích đất 114 m²</p><p>Diện tích sử dụng 155 m²</p></section>
<p>Mô tả chi tiết: Giá còn lại thanh toán 2 tỷ, chiết khấu 10% đến khi bàn giao.
Lưu ý mô tả không phải giá tổng. </p>
<section><h2>Thông tin dự án</h2>Izumi City</section></main></body></html>"""

class Raw:
    def __init__(self,body):self.stream=io.BytesIO(body.encode())
    def read(self,count,decode_content=False):return self.stream.read(count)
class Response:
    def __init__(self,body=HTML,url=URL,status=200):
        self.raw=Raw(body);self.url=url;self.status_code=status;self.encoding="utf-8"
class Session:
    def __init__(self,pages):self.pages=pages
    def get(self,url,**kwargs):
        v=self.pages[url]
        return v

class LandedPriceTests(unittest.TestCase):
    def test_sale_asking_not_downpayment_in_title(self):
        row,state=parse_detail(HTML,URL,PROJECT,NOW)
        self.assertEqual(state,"qualified-source-evidence")
        self.assertEqual(row["listing_price_vnd"],7_600_000_000)
        self.assertEqual(row["listed_land_area_sqm"],114)
        self.assertEqual(row["value_vnd_per_land_m2"],66_670_000)
        self.assertEqual(row["product_type"],"townhouse")
        self.assertEqual(row["source_updated_date"],"2026-11-01")
        self.assertNotIn("average_asp",row)
        self.assertIsNone(row["subproject_id"])

    def test_publisher_date_is_absolute_not_crawl_date(self):
        undated=HTML.replace('<meta property="article:modified_time" content="2026-11-01T08:01:00+07:00">','')
        row,status=parse_detail(undated,URL,PROJECT,NOW)
        self.assertIsNone(row)
        self.assertEqual(status,"absolute-publisher-update-date-unavailable")

    def test_mismatched_display_rate_rejected(self):
        row,state=parse_detail(HTML.replace("66,67 triệu","89,00 triệu"),URL,PROJECT,NOW)
        self.assertIsNone(row)
        self.assertEqual(state,"price-area-rate-mismatch")

    def test_wrong_project_card_rejected_even_if_title_matches(self):
        html=HTML.replace("Thông tin dự án</h2>Izumi City","Thông tin dự án</h2>Aqua City")
        self.assertEqual(parse_detail(html,URL,PROJECT,NOW)[1],"project-not-on-listing-project-card")

    def test_wrong_property_type_and_floor_area_rejected(self):
        bad=HTML.replace("Loại hình Nhà phố liền kề","Loại hình Nhà ở xã hội")
        self.assertEqual(parse_detail(bad,URL,PROJECT,NOW)[1],"unclassified-landed-product")
        no_land=HTML.replace("Diện tích đất 114 m²","Diện tích sử dụng 114 m²")
        self.assertEqual(parse_detail(no_land,URL,PROJECT,NOW)[1],"no-explicit-land-area")

    def test_too_old_update_date_rejected(self):
        self.assertEqual(parse_detail(HTML.replace("2026-11-01","2026-07-01"),URL,PROJECT,NOW)[1],
                         "absolute-publisher-update-date-unavailable")

    def test_redirect_host_rejected(self):
        self.assertIsNone(site_url("http://www.nhatot.com/mua-ban-nha-dat-x/12345678.htm",True))
        self.assertIsNone(site_url("https://evil.test/mua-ban-nha-dat-x/12345678.htm",True))
        self.assertIsNone(site_url(URL+"?redirect=1",True))
        self.assertIsNone(site_url("https://www.nhatot.com/mua-ban-can-ho-chung-cu/135405361.htm",True))

    def test_catalog_discovery_limited_and_safe(self):
        page='<a href="'+URL+'">listing</a>'*4+'<a href="https://evil.test/42">bad</a>'
        self.assertEqual(discover(page,INDEX),[URL])

    def test_requires_two_distinct_runs_at_least_hour_apart(self):
        row,_=parse_detail(HTML,URL,PROJECT,NOW)
        first,published,decisions=evaluate({"proofs":{}},[],[row],NOW,"run-a")
        self.assertFalse(published)
        same,published,_=evaluate(first,[],[row],NOW+timedelta(minutes=20),"run-b")
        self.assertFalse(published)
        next_state,published,_=evaluate(same,[],[row],NOW+timedelta(hours=2),"run-c")
        self.assertEqual(len(published),1)
        self.assertEqual(published[0]["verification_run_ids"],["run-b","run-c"])
        _,again,_=evaluate(next_state,published,[row],NOW+timedelta(hours=3),"run-d")
        self.assertFalse(again)

    def test_price_revision_resets_evidence(self):
        row,_=parse_detail(HTML,URL,PROJECT,NOW)
        first,_,_=evaluate({"proofs":{}},[],[row],NOW,"one")
        change={**row,"listing_price_vnd":8_000_000_000}
        proof,released,_=evaluate(first,[],[change],NOW+timedelta(hours=2),"two")
        self.assertFalse(released)
        _,released,_=evaluate(proof,[],[change],NOW+timedelta(hours=4),"three")
        self.assertEqual(len(released),1)

    def test_access_failures_do_not_delete_existing_evidence(self):
        prior_row,_=parse_detail(HTML,URL,PROJECT,NOW)
        prior={**prior_row,"id":"saved-offer-1"}
        config={"targets":[{"project_id":"izumi-city","project_name":"Izumi City",
                            "catalog_url":INDEX,"seed_urls":[URL]}]}
        pages={INDEX:Response("<html><body>No new listings</body></html>",url=INDEX),
               URL:Response("",status=403)}
        _,output,health=run(config,{"data":[PROJECT]},{"proofs":{}},{"data":[prior]},
                            Session(pages),NOW,"offline")
        self.assertEqual(output["record_count"],1)
        self.assertEqual(health["released_new_individual_offers"],0)
        self.assertEqual(health["sources"][0]["reasons"]["http-403"],1)

    def test_mixed_category_aqua_social_housing_not_landed(self):
        aqua={"id":"aqua-city","name":"Aqua City","segment_ids":["landed"]}
        wrong=HTML.replace("Izumi City","Aqua City").replace("Loại hình Nhà phố liền kề","Loại hình Nhà ở xã hội")
        url="https://www.nhatot.com/mua-ban-can-ho-chung-cu-thanh-pho-bien-hoa-dong-nai/135405361.htm"
        self.assertEqual(parse_detail(wrong,url,aqua,NOW)[1],"unclassified-landed-product")

if __name__=="__main__":
    unittest.main()
