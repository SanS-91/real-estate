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

    def test_upfront_amount_equal_header_price_rejected(self):
        row,status=parse_detail(
            page(price="4,8 tỷ",title="Mua Izumi City chỉ đóng tổng 4,8 tỷ ban đầu"),
            URL,PROJECT,NOW)
        self.assertIsNone(row)
        self.assertEqual(status,"header-total-matches-upfront-only-title")
        row,status=parse_detail(
            page(title="Giá từ 7 tỷ, giỏ hàng nhiều căn Izumi City"),
            URL,PROJECT,NOW)
        self.assertIsNone(row)
        self.assertEqual(status,"non-single-unit-sale-heading")

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


    def test_waterpoint_publisher_alias_exact_not_aqua_city(self):
        waterpoint={"id":"waterpoint","name":"Waterpoint","segment_ids":["landed"]}
        listing=page(project="Khu Đô Thị Waterpoint")
        row,status=parse_detail(listing,URL,waterpoint,NOW,"Khu Đô Thị Waterpoint")
        self.assertEqual(status,"qualified-unexpired-landed-offer")
        self.assertEqual(row["project_id"],"waterpoint")
        other=page(project="Aqua City")
        self.assertEqual(parse_detail(other,URL,waterpoint,NOW,"Khu Đô Thị Waterpoint")[1],
                         "project-not-explicit-in-basic-info")
        self.assertEqual(parse_detail(listing,URL,waterpoint,NOW)[1],
                         "project-not-explicit-in-basic-info")

    def test_global_city_villa_category_allowed_only_correct_project(self):
        catalog="https://muaban.net/bat-dong-san/ban-biet-thu-villa-penthouse-du-an-the-global-city-quan-2-ho-chi-minh"
        url=catalog+"/can-biet-thu-the-global-city-song-lap-id71299999"
        self.assertEqual(safe_url(catalog),catalog)
        self.assertEqual(safe_url(url,True),url)
        global_city={"id":"the-global-city","name":"The Global City","segment_ids":["landed"]}
        html=page(project="The Global City",kind="Biệt thự").replace("Mã tin 71272223","Mã tin 71299999")
        row,status=parse_detail(html,url,global_city,NOW)
        self.assertEqual(status,"qualified-unexpired-landed-offer")
        self.assertEqual(row["product_type"],"villa")

    def test_regional_index_preselects_waterpoint_links_not_nearby_projects(self):
        catalog="https://muaban.net/bat-dong-san/ban-nha-mat-tien-huyen-ben-luc-long-an"
        good=catalog+"/ban-nha-pho-waterpoint-id71288001"
        unrelated=catalog+"/nha-pho-du-an-khac-id71288002"
        html=('<a href="'+unrelated+'">Nhà tại Bến Lức</a>'+
              '<a href="'+good+'">BÁN nhà phố vườn Waterpoint</a>'+
              '<a href="'+unrelated+'">Waterpoint gần khu vực này</a>')
        self.assertEqual(discover(html,catalog,project_name="Waterpoint",regional=True),[good])
        # A match on a catalog link is only a candidate; the offer still
        # fails if its structured project field is missing or belongs elsewhere.
        house={"id":"waterpoint","name":"Waterpoint","segment_ids":["landed"]}
        _,decision=parse_detail(page(project="Another Residence"),URL,house,NOW,
                                "Khu Đô Thị Waterpoint")
        self.assertEqual(decision,"project-not-explicit-in-basic-info")

    def test_regional_discovery_cannot_override_exact_project_card(self):
        catalog="https://muaban.net/bat-dong-san/ban-nha-mat-tien-huyen-ben-luc-long-an"
        self.assertEqual(safe_url(catalog),catalog)
        other="https://muaban.net/bat-dong-san/ban-nha-mat-tien-huyen-ben-luc-long-an/other-project-id71289999"
        sample='<a href="'+other+'">Giá rẻ Waterpoint</a>'
        self.assertEqual(discover(sample,catalog),[other])
        waterpoint={"id":"waterpoint","name":"Waterpoint","segment_ids":["landed"]}
        row,status=parse_detail(page(project="Other Project"),URL,waterpoint,NOW,"Khu Đô Thị Waterpoint")
        self.assertIsNone(row)
        self.assertEqual(status,"project-not-explicit-in-basic-info")


    def test_changed_price_deactivates_old_offer_immediately(self):
        old_row,_=parse_detail(page(),URL,PROJECT,NOW)
        stored={**old_row,"id":"old-record","verified_at":NOW.isoformat(),
                "review_status":"automated-two-hosted-dated-checks",
                "verification_run_ids":["earlier","later"],
                "source_status":"confirmed-match"}
        target={"project_id":"izumi-city","publisher_project_name":"Izumi City",
                "catalog_url":CATALOG,"seed_urls":[URL]}
        changed=Session({CATALOG:Response("",url=CATALOG,status=403),
                         URL:Response(page(price="12,1 tỷ"),url=URL)})
        _,records,health=run({"targets":[target]},{"data":[PROJECT]},{"proofs":{}},
                             {"data":[stored]},changed,NOW+timedelta(hours=1),"changed-price")
        self.assertEqual(records["record_count"],1)
        self.assertEqual(records["data"][0]["source_status"],"changed-pending-verification")
        self.assertEqual(health["qualified_offers"],1)
        blocked=Session({CATALOG:Response("",url=CATALOG,status=403),
                         URL:Response("",url=URL,status=403)})
        _,records,_=run({"targets":[target]},{"data":[PROJECT]},{"proofs":{}},
                        records,blocked,NOW+timedelta(hours=2),"blocked")
        self.assertEqual(records["data"][0]["source_status"],"not-reconfirmed")

    def test_aqua_city_catalog_and_unrelated_recommendations_are_isolated(self):
        aqua={"id":"aqua-city","name":"Aqua City","segment_ids":["landed"]}
        catalog="https://muaban.net/bat-dong-san/ban-nha-mat-tien-du-an-aqua-city-tp-bien-hoa-dong-nai"
        villa_catalog="https://muaban.net/bat-dong-san/ban-biet-thu-villa-penthouse-du-an-aqua-city-tp-bien-hoa-dong-nai"
        ad="https://muaban.net/bat-dong-san/ban-nha-mat-tien-tp-bien-hoa-dong-nai/ban-shophouse-aquacity-truc-duong-chinh-45m-khu-stella-id69617830"
        self.assertEqual(safe_url(catalog),catalog)
        self.assertEqual(safe_url(villa_catalog),villa_catalog)
        self.assertEqual(safe_url(ad,True),ad)
        # A matching headline is NOT project identity. It must appear in the
        # listing's structured 'Dự án' field, with matching property class.
        wrong=page(project="Khu Nhà Ở Cao Cấp Hưng Phú 2",
                   title="Gần Aqua City - nhà đẹp, view thoáng")
        self.assertEqual(parse_detail(wrong,URL,aqua,NOW)[1],
                         "project-not-explicit-in-basic-info")
        actual=page(project="Aqua City",kind="Biệt thự")
        listing,status=parse_detail(actual,URL,aqua,NOW)
        self.assertEqual(status,"qualified-unexpired-landed-offer")
        self.assertEqual(listing["project_id"],"aqua-city")
        self.assertEqual(listing["product_type"],"villa")
        self.assertEqual(parse_detail(page(project="Aqua City",kind="Căn hộ"),
            URL,aqua,NOW)[1],"non-landed-or-ambiguous-product")

    def test_source_recheck_heartbeat_requires_live_publisher_page(self):
        original,_=parse_detail(page(),URL,PROJECT,NOW)
        stored={**original,"id":"saved-one","verified_at":"2026-10-31T08:00:00+00:00",
                "last_source_verified_at":"2026-10-31T08:00:00+00:00"}
        target={"project_id":"izumi-city","publisher_project_name":"Izumi City",
                "catalog_url":CATALOG,"seed_urls":[URL]}
        good=Session({CATALOG:Response("",url=CATALOG,status=403),
                      URL:Response(page(),url=URL)})
        _state,output,health=run({"targets":[target]},{"data":[PROJECT]},{"proofs":{}},
                                 {"data":[stored]},good,NOW,"hosted-1")
        self.assertEqual(output["record_count"],1)
        self.assertEqual(output["data"][0]["last_source_verified_at"],NOW.isoformat())
        self.assertEqual(output["data"][0]["source_status"],"confirmed-match")
        self.assertEqual(health["qualified_offers"],1)

        missing=Session({CATALOG:Response("",url=CATALOG,status=403),
                         URL:Response("",url=URL,status=403)})
        _,stale,health=run({"targets":[target]},{"data":[PROJECT]},{"proofs":{}},
                           output,missing,NOW+timedelta(hours=2),"hosted-2")
        self.assertEqual(stale["record_count"],1)
        self.assertEqual(stale["data"][0]["last_source_verified_at"],NOW.isoformat())
        self.assertEqual(stale["data"][0]["source_status"],"not-reconfirmed")
        self.assertEqual(health["qualified_offers"],0)

if __name__=="__main__":
    unittest.main()
