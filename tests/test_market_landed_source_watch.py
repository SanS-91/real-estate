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

if __name__=="__main__":
    unittest.main()
