"""Tests for safe market landed source watching: no price promotion."""
import io
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from market_landed_source_watch import check_target, run, permitted, text_fingerprint

NOW="2026-11-02T08:20:00+00:00"
URL="https://www.namlongvn.com/en/township-residential/izumi-city-township/"
PROJECT={"id":"izumi-city","name":"Izumi City","official_url":URL,"segment_ids":["township","landed"]}
TARGET={"project_id":"izumi-city","asset_type":"landed","source_id":"nam-long-official","source_url":URL,"allowed_host":"namlongvn.com"}
HTML="<html><body><main><h1>Izumi City</h1><p>"+("An integrated developer township with amenities and landscape. "*5)+"</p></main></body></html>"

class RawBytes:
    def __init__(self, body):
        self.buffer=io.BytesIO(body.encode("utf-8"))
    def read(self, size, decode_content=False):
        return self.buffer.read(size)

class Response:
    def __init__(self, body=HTML, code=200,url=URL):
        self.url=url
        self.status_code=code
        self.encoding="utf-8"
        self.raw=RawBytes(body)

class Session:
    def __init__(self,response):
        self.response=response
    def get(self,*args,**kwargs):
        return self.response

class WatchTests(unittest.TestCase):
    def test_strict_source_host(self):
        self.assertTrue(permitted(URL,"namlongvn.com"))
        self.assertFalse(permitted("https://example.net/en/township-residential/izumi-city-township/","namlongvn.com"))
        self.assertFalse(permitted(URL+"?version=1","namlongvn.com"))
        self.assertFalse(permitted("http://www.namlongvn.com/test","namlongvn.com"))

    def test_valid_source_does_not_publish_prices(self):
        row=check_target(TARGET,PROJECT,{},Session(Response()),NOW)
        self.assertEqual(row["status"],"source-page-reachable")
        self.assertEqual(row["candidate_price_records"],0)
        self.assertFalse(row["price_data_published"])
        self.assertFalse(row["content_changed"])

    def test_source_change_marks_manual_review_only(self):
        previous=check_target(TARGET,PROJECT,{},Session(Response()),NOW)
        changed=HTML.replace("amenities and landscape","parks and school district")
        row=check_target(TARGET,PROJECT,previous,Session(Response(changed)),NOW)
        self.assertTrue(row["content_changed"])
        self.assertTrue(row["needs_manual_review"])
        self.assertEqual(row["candidate_price_records"],0)

    def test_untrusted_redirect_and_error_are_not_reachable(self):
        row=check_target(TARGET,PROJECT,{},Session(Response(url="https://untrusted.example/")),NOW)
        self.assertEqual(row["status"],"redirect-outside-approved-publisher")
        blocked=check_target(TARGET,PROJECT,{},Session(Response(code=403)),NOW)
        self.assertEqual(blocked["status"],"access-unavailable")
        self.assertFalse(blocked["needs_manual_review"])

    def test_missing_title_refused(self):
        self.assertIsNone(text_fingerprint("<html><body> "+("hello "*120)+"</body></html>")[0])

    def test_registry_identity_prevents_unrelated_source(self):
        wrong={**PROJECT,"official_url":"https://example.net/another"}
        self.assertEqual(check_target(TARGET,wrong,{},Session(Response()),NOW)["status"],"unapproved-source-identity")

    def test_registry_landed_scope_required(self):
        wrong={**PROJECT,"segment_ids":["apartment"]}
        with self.assertRaisesRegex(ValueError,"wrong-product-scope"):
            run({"targets":[TARGET]},{"data":[wrong]},{"projects":[]},Session(Response()),NOW)

    def test_complete_run_has_no_price_fields(self):
        out=run({"targets":[TARGET]},{"data":[PROJECT]},{"projects":[]},Session(Response()),NOW)
        self.assertEqual(out["projects_monitored"],1)
        self.assertEqual(out["published_prices"],0)
        self.assertFalse(any("value_vnd_per_m2" in item or "asp" in item for item in out["projects"]))


    def test_official_aqua_article_h2_is_accepted_but_generic_h1_is_not(self):
        aqua_url="https://www.novaland.com.vn/tin-tuc-1/thong-tin-novaland/tin-du-an/aqua-city-chinh-thuc-mo-ban-tro-lai-tu-3110-khoi-thong-dong-thu-hang-tram-nghin-ty-dong"
        target={"project_id":"aqua-city","asset_type":"landed","source_id":"novaland-official",
                "source_url":aqua_url,"allowed_host":"novaland.com.vn",
                "page_type":"project-news-article",
                "source_title_hint":"Aqua City chính thức mở bán trở lại"}
        project={"id":"aqua-city","name":"Aqua City","official_url":aqua_url,"segment_ids":["landed"]}
        html=("<html><main><h1>Tin Novaland</h1><article>"
              "<h2>Aqua City chính thức mở bán trở lại từ 31/10</h2>"+
              "<p>Thông báo của chủ đầu tư Aqua City, với nhiều cập nhật về hoạt động dự án. </p>"*5+
              "</article></main></html>")
        row=check_target(target,project,{},Session(Response(html,url=aqua_url)),NOW)
        self.assertEqual(row["status"],"source-page-reachable")
        self.assertIn("Aqua City",row["page_headline"])
        false_page=html.replace("Aqua City chính thức mở bán trở lại","Tin dự án khác")
        rejected=check_target(target,project,{},Session(Response(false_page,url=aqua_url)),NOW)
        self.assertEqual(rejected["status"],"project-headline-not-confirmed")
        self.assertEqual(rejected["candidate_price_records"],0)

    def test_tls_valid_same_publisher_fallback_without_verify_false(self):
        from requests.exceptions import SSLError
        fallback="https://gamudaland.com.vn/en/developments/springville"
        canonical="https://www.gamudaland.com.vn/vn/developments/township/springville"
        target={"project_id":"springville","asset_type":"landed","source_id":"gamuda-land-official",
                "source_url":canonical,"allowed_host":"gamudaland.com.vn",
                "page_type":"project-landing","fallback_urls":[fallback]}
        project={"id":"springville","name":"Springville","official_url":canonical,
                 "segment_ids":["landed","apartment"]}
        good=HTML.replace("Izumi City","Springville")
        class TwoSources:
            def __init__(self):self.urls=[]
            def get(self,url,**kwargs):
                self.urls.append(url)
                self_test.assertNotIn("verify",kwargs)
                if url==canonical:raise SSLError("certificate verify failed")
                return Response(good,url=fallback)
        self_test=self
        session=TwoSources()
        row=check_target(target,project,{},session,NOW)
        self.assertEqual(row["status"],"source-page-reachable")
        self.assertEqual(session.urls,[canonical,fallback])
        self.assertEqual(row["effective_source_url"],fallback)
        self.assertEqual(len(row["attempts"]),2)
        self.assertEqual(row["candidate_price_records"],0)

    def test_untrusted_fallback_is_rejected_before_network(self):
        target={**TARGET,"fallback_urls":["https://other-developer.example/path"]}
        class NoNetwork:
            def get(self,*args,**kwargs):raise AssertionError("No network for disallowed fallback")
        row=check_target(target,PROJECT,{},NoNetwork(),NOW)
        self.assertEqual(row["status"],"unapproved-fallback")
        self.assertFalse(row["needs_manual_review"])

    def test_new_fallback_does_not_create_false_content_change(self):
        target={**TARGET,"fallback_urls":["https://namlongvn.com/en/township-residential/izumi-city-township/"]}
        previous={"project_id":"izumi-city","source_url":URL,
                  "effective_source_url":URL,"content_sha256":"previous-content"}
        # Source switch is not a market event; every price remains unverified.
        from requests.exceptions import SSLError
        class Fallback:
            def get(self,url,**kwargs):
                if url==URL:raise SSLError("old host error")
                return Response(HTML,url=url)
        row=check_target(target,PROJECT,previous,Fallback(),NOW)
        self.assertEqual(row["status"],"source-page-reachable")
        self.assertFalse(row["content_changed"])
        self.assertFalse(row["needs_manual_review"])

if __name__=="__main__":
    unittest.main()
