"""Rever individual listing discovery must reject wrong project and old/ambiguous quotes."""
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from market_rever_project_listings import discover, parse_detail, evaluate, run, safe_url

NOW=datetime(2026,10,9,8,0,tzinfo=timezone.utc)
ROOT="https://rever.vn"
INDEX=ROOT+"/s/eaton-park/mua/can-ho"
LISTING=ROOT+"/mua/can-ho-eaton-park-dien-tich-72-m2"
HTML="""<html><body><main><h1>Căn hộ Eaton Park, diện tích 72 m²</h1>
Mã nhà đất: A02199312 Cập nhật: 28/07/2026
8.9 tỷ 123.61 triệu/m² 2 2 72m²
Thông tin đã xác thực, hình ảnh thực, vị trí chính xác, giá đúng
Tổng quan CĂN HỘ EATON PARK Diện tích: 72m²
Thông tin cơ bản Loại hình Căn hộ Phòng ngủ 2
Dự án Eaton Park Giá bán 8.9 tỷVND
</main></body></html>"""


class ReverSourceTests(unittest.TestCase):
    def test_dynamic_links_dedup_and_host(self):
        html='<a href="/mua/can-ho-eaton-park-dien-tich-72-m2">unit</a>'*3
        html+='<a href="https://evil.invalid/mua/listing">unsafe</a>'
        self.assertEqual(discover(html, INDEX),[LISTING])
        self.assertIsNone(safe_url("https://evil.invalid/mua/a",listing=True))
        self.assertIsNone(safe_url("https://rever.vn/mua/a?redirect=https://evil.invalid",listing=True))

    def test_price_date_scope_from_individual_listing(self):
        row, status=parse_detail(HTML,LISTING,"Eaton Park","eaton-park",NOW)
        self.assertEqual(status,"parsed-listing")
        self.assertEqual(row["listing_id"],"A02199312")
        self.assertEqual(row["source_updated_date"],"2026-07-28")
        self.assertEqual(row["listing_price_vnd"],8_900_000_000)
        self.assertEqual(row["value_vnd_per_m2"],123_610_000)
        self.assertEqual(row["listed_area_sqm"],72)
        self.assertNotIn("average_asp",row)

    def test_cross_project_recommendations_never_pass(self):
        self.assertEqual(parse_detail(HTML,LISTING,"The Global City","the-global-city",NOW)[1],"project-not-explicit")
        self.assertEqual(parse_detail(HTML.replace("Dự án Eaton Park Giá bán","Dự án Palm Heights Giá bán"),
            LISTING,"Eaton Park","eaton-park",NOW)[1],"project-not-explicit")
        self.assertEqual(parse_detail(HTML.replace("Căn hộ Eaton Park","Cho thuê căn hộ Eaton Park"),
            LISTING,"Eaton Park","eaton-park",NOW)[1],"wrong-product-type")
        self.assertEqual(parse_detail(HTML.replace("123.61 triệu","160.00 triệu"),
            LISTING,"Eaton Park","eaton-park",NOW)[1],"inconsistent-price-per-sqm-and-area")

    def test_two_runs_at_least_one_hour_and_source_date_freshness(self):
        row,status=parse_detail(HTML,LISTING,"Eaton Park","eaton-park",NOW)
        self.assertEqual(status,"parsed-listing")
        a, rows, decisions=evaluate({},[],[row],NOW,"1")
        self.assertFalse(rows)
        b, rows, decisions=evaluate(a,[],[row],NOW+timedelta(minutes=30),"2")
        self.assertFalse(rows)
        c, rows, decisions=evaluate(b,[],[row],NOW+timedelta(hours=2),"3")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["market_layer"],"individual-listing-asking")
        self.assertEqual(rows[0]["verification_run_ids"],["2","3"])
        _,dup,decisions=evaluate(c,rows,[row],NOW+timedelta(hours=3),"4")
        self.assertFalse(dup)
        old={**row,"source_updated_date":"2024-07-28","listing_id":"A02199311"}
        _,unverified,decisions=evaluate({},[],[old],NOW,"1")
        self.assertEqual(decisions[0]["decision"],"historical-listing-not-current")
        self.assertFalse(unverified)

    def test_source_dated_price_revision_is_append_only(self):
        first,_=parse_detail(HTML,LISTING,"Eaton Park","eaton-park",NOW)
        saved={
            **first, "id":"rever-a02199312-old", "review_status":"automated-two-hosted-checks",
            "verification_run_ids":["old-a","old-b"],
            "review_date":"2026-08-01", "verified_at":"2026-08-01T08:00:00+00:00"
        }
        revised={**first,"source_updated_date":"2026-10-09",
                 "listing_price_vnd":9_000_000_000,"value_vnd_per_m2":125_000_000}
        # Existing unit cannot be re-dated from an unchanged source date.
        conflicting={**revised,"source_updated_date":first["source_updated_date"]}
        st,accepted,decisions=evaluate({},[saved],[conflicting],NOW,"revision-1")
        self.assertEqual(decisions[0]["decision"],"publisher-date-not-newer-than-recorded")
        self.assertFalse(accepted)
        st,accepted,_=evaluate(st,[saved],[revised],NOW,"revision-2")
        self.assertFalse(accepted)
        st,accepted,decisions=evaluate(st,[saved],[revised],NOW+timedelta(hours=2),"revision-3")
        self.assertEqual(len(accepted),1)
        self.assertEqual(accepted[0]["source_updated_date"],"2026-10-09")
        self.assertEqual(decisions[0]["decision"],"independent-live-listing-verified")
        # Two publisher-dated price versions remain independent unit evidence.
        _,dup,d=evaluate(st,[saved]+accepted,[revised],NOW+timedelta(hours=3),"revision-4")
        self.assertFalse(dup)
        self.assertEqual(d[0]["decision"],"previously-recorded")

    def test_long_term_history_is_not_silently_truncated(self):
        saved=[{
          **parse_detail(HTML,LISTING,"Eaton Park","eaton-park",NOW)[0],
          "id":f"verified-old-{idx}",
          "listing_id":f"A021{idx:05d}",
          "source_updated_date":"2026-09-01",
          "review_status":"automated-two-hosted-checks",
          "verification_run_ids":["a","b"],
        } for idx in range(255)]
        cfg={"targets":[{"project_id":"eaton-park","publisher_project_name":"Eaton Park","url":INDEX}]}
        result,_,report=run(cfg,{"data":saved},{},
          lambda url,listing:(None,"access-blocked"),NOW,"probe")
        self.assertEqual(result["record_count"],255)
        self.assertEqual(result["data"][0]["id"],"verified-old-0")
        self.assertEqual(report["accepted_new_individual_listings"],0)

    def test_new_source_target_registry_has_real_exact_rever_catalogs(self):
        import json
        settings=json.loads((Path(__file__).resolve().parents[1]/
           "config/market-rever-listing-targets.json").read_text())
        mapping={x["project_id"]:x for x in settings["targets"]}
        for pid,slug in (("the-9-stellars","the-9-stellars"),
                         ("mizuki-park","mizuki-park"),
                         ("vinhomes-grand-park","vinhomes-grand-park")):
            self.assertEqual(mapping[pid]["url"],
                             f"https://rever.vn/s/{slug}/mua/can-ho")
            self.assertIsNotNone(safe_url(mapping[pid]["url"]))
        self.assertEqual(len(mapping),len(settings["targets"]))

    def test_runner_fetch_outage_only_reports_health(self):
        config={"targets":[{"project_id":"eaton-park","publisher_project_name":"Eaton Park","url":INDEX}]}
        prod,state,report=run(config,{"data":[]},{},lambda url,listing:(None,"access-blocked"),
                              NOW,"a")
        self.assertEqual(report["sources"][0]["index_status"],"access-blocked")
        self.assertEqual(report["accepted_new_individual_listings"],0)
        self.assertEqual(prod["record_count"],0)
        self.assertFalse(report["production_project_aggregates_changed"])

    def test_real_listing_discovery_two_iterations(self):
        cfg={"targets":[{"project_id":"eaton-park","publisher_project_name":"Eaton Park","url":INDEX}]}
        fake=lambda url,listing: (HTML if listing else f'<a href="{LISTING}">Eaton listing</a>',"reachable")
        a,s,report=run(cfg,{"data":[]},{},fake,NOW,"100")
        self.assertEqual(report["listing_urls_discovered"],1)
        self.assertEqual(report["qualified_current_or_historical"],1)
        self.assertEqual(report["accepted_new_individual_listings"],0)
        b,ss,report=run(cfg,a,s,fake,NOW+timedelta(hours=2),"101")
        self.assertEqual(b["record_count"],1)
        self.assertEqual(report["accepted_new_individual_listings"],1)


if __name__=="__main__":
    unittest.main()
