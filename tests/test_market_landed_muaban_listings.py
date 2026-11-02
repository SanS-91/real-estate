"""Muaban landed single-offer contract: no publisher expiry bypass."""
import io
import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from market_landed_muaban_listings import parse_detail, safe_url, discover, run
from market_landed_unit_listings import evaluate

NOW=datetime(2026,11,2,8,0,tzinfo=timezone.utc)
ROOT="https://muaban.net/bat-dong-san/"
CATALOG=ROOT+"ban-nha-mat-tien-du-an-izumi-city-tp-bien-hoa-dong-nai"
URL=CATALOG+"/nha-pho-izumi-city-mat-tien-kenh-canh-quan-lon-song-giua-mang-xanh-id71272223"
PROJECT={"id":"izumi-city","name":"Izumi City","segment_ids":["landed","township"]}

def page(price="11,3 tỷ",project="Izumi City",area="136,5 m²",
         kind="Nhà mặt tiền",start="06/10/2026",expiry="05/11/2026",
         title="Nhà Phố Izumi City - Chỉ đóng 15% lúc nhận nhà",details="View kênh cảnh quan, giá trị định cư ven sông"):
    return f"""<html><body><main><h1>{title}</h1>
    {price}
    Đường Hương Lộ 2, Đồng Nai
    Cập nhật: Hôm nay
    Thông tin chi tiết
    {details}
    Thông tin cơ bản
    Loại hình nhà ở:{kind}
    Dự án:{project}
    Diện tích đất:{area} (7.0x19.5)
    Số phòng ngủ:4 phòng
    Thông tin dự án
    {project}
    Ngày bắt đầu {start}
    Ngày hết hạn {expiry}
    Mã tin 71272223
    </main></body></html>"""

class Raw:
    def __init__(self,body):self.io=io.BytesIO(body.encode())
    def read(self,n,decode_content=False):return self.io.read(n)
class Response:
    def __init__(self,body=None,url=URL,status=200):
        self.url=url;self.encoding="utf-8";self.status_code=status
        self.raw=Raw(body if body is not None else page())
class Session:
    def __init__(self,responses):self.responses=responses
    def get(self,url,**kwargs):return self.responses[url]

class MuabanLandedTests(unittest.TestCase):
    def test_individual_land_rate_derived_from_total(self):
        row,status=parse_detail(page(),URL,PROJECT,NOW)
        self.assertEqual(status,"qualified-unexpired-landed-offer")
        self.assertEqual(row["listing_price_vnd"],11_300_000_000)
        self.assertEqual(row["listed_land_area_sqm"],136.5)
        self.assertEqual(row["value_vnd_per_land_m2"],round(11_300_000_000/136.5))
        self.assertEqual(row["source_expiration_date"],"2026-11-05")
        self.assertEqual(row["source_listed_date"],"2026-10-06")
        self.assertIsNone(row["subproject_id"])
        self.assertNotIn("average_asp",row)

    def test_expiry_mandatory_even_if_updated_today(self):
        self.assertEqual(parse_detail(page(expiry="01/11/2026"),URL,PROJECT,NOW)[1],"publisher-expired")
        self.assertEqual(parse_detail(page(expiry=""),URL,PROJECT,NOW)[1],"missing-or-conflicting-publisher-validity")
        self.assertEqual(parse_detail(page(start="11/11/2026",expiry="20/11/2026"),URL,PROJECT,NOW)[1],"future-publisher-start")

    def test_price_is_from_header_not_downpayment_title(self):
        row,status=parse_detail(page(title="Chỉ thanh toán 2,7 tỷ để nhận nhà, giá chiết khấu 20%"),URL,PROJECT,NOW)
        self.assertEqual(status,"qualified-unexpired-landed-offer")
        self.assertEqual(row["listing_price_vnd"],11_300_000_000)

    def test_wrong_project_and_landed_type_rejected(self):
        self.assertEqual(parse_detail(page(project="Aqua City"),URL,PROJECT,NOW)[1],"project-not-explicit-in-basic-info")
        self.assertEqual(parse_detail(page(kind="Nhà ở xã hội"),URL,PROJECT,NOW)[1],"non-landed-or-ambiguous-product")
        self.assertEqual(parse_detail(page(kind="Căn hộ"),URL,PROJECT,NOW)[1],"non-landed-or-ambiguous-product")

    def test_floor_area_not_substitute_land_area(self):
        row,status=parse_detail(page(area=""),URL,PROJECT,NOW)
        self.assertEqual(status,"no-land-area")
        self.assertIsNone(row)

    def test_basket_ads_and_conflicting_total_price_rejected(self):
        self.assertEqual(parse_detail(page(details="Giỏ hàng tổng hợp nhiều căn 7,9 tỷ và 8,3 tỷ"),URL,PROJECT,NOW)[1],
                         "multiple-units-in-one-ad")
        self.assertEqual(parse_detail(page(details="Giá sau CSBH: 8,7 tỷ"),URL,PROJECT,NOW)[1],
                         "conflicting-total-price-in-description")

    def test_url_whitelist_and_discovery(self):
        self.assertIsNone(safe_url(URL+"?u=abc",True))
        self.assertIsNone(safe_url("https://muaban.net.evil.test"+URL.split("muaban.net")[1],True))
        self.assertIsNone(safe_url("https://muaban.net/bat-dong-san/ban-dat-du-an-izumi",False))
        self.assertEqual(discover('<a href="'+URL+'">ad</a>'*3,CATALOG),[URL])

    def test_no_release_first_run_then_two_identical_hosted_checks(self):
        row,_=parse_detail(page(),URL,PROJECT,NOW)
        a,one,_=evaluate({"proofs":{}},[],[row],NOW,"run-1")
        self.assertEqual(one,[])
        b,two,_=evaluate(a,[],[row],NOW+timedelta(hours=2),"run-2")
        self.assertEqual(len(two),1)
        self.assertEqual(two[0]["review_status"],"automated-two-hosted-dated-checks")
        self.assertEqual(two[0]["verification_run_ids"],["run-1","run-2"])

    def test_catalog_unavailable_keeps_seed_and_old_history(self):
        target={"project_id":"izumi-city","project_name":"Izumi City","catalog_url":CATALOG,"seed_urls":[URL]}
        session=Session({CATALOG:Response("",url=CATALOG,status=403),URL:Response("",url=URL,status=403)})
        already={"data":[{"id":"old-offer","project_id":"izumi-city"}]}
        state,out,health=run({"targets":[target]},{"data":[PROJECT]},{"proofs":{}},already,session,NOW,"r1")
        self.assertEqual(out["record_count"],1)
        self.assertEqual(health["sources"][0]["reasons"],{"http-403":1})
        self.assertEqual(health["published_new_offers"],0)

if __name__=="__main__":
    unittest.main()
