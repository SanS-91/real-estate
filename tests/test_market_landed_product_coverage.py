"""Source-typed subdivision product monitor must never manufacture price ranges."""
import io
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from market_landed_product_coverage import run,inspect,evidence,has_phrase
from market_landed_source_watch import permitted

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/"config/market-landed-product-scopes.json").read_text(encoding="utf-8"))
PROJECTS=json.loads((ROOT/"data/mock/market/projects.json").read_text(encoding="utf-8"))
TARGET=CONFIG["sources"][0]
PROJECT=next(x for x in PROJECTS["data"] if x["id"]==TARGET["project_id"])
T="<html><body><main><h1>Izumi Gardenia</h1><p>"+("275 commercial townhouses and garden townhouses are located in the compound. "*5)+"</p></main></body></html>"

class Stream:
    def __init__(self,html):self.fp=io.BytesIO(html.encode())
    def read(self,n,decode_content=False):return self.fp.read(n)

class Response:
    def __init__(self,html=T,url=TARGET["source_url"],status=200):
        self.url=url
        self.raw=Stream(html)
        self.encoding="utf-8"
        self.status_code=status

class Session:
    def __init__(self,response):self.response=response
    def get(self,*args,**kwargs):return self.response

class ProductEvidenceTests(unittest.TestCase):
    def test_confirm_two_distinct_types_without_prices(self):
        found,status=evidence(T,TARGET)
        self.assertEqual(status,"source-checked")
        self.assertEqual(found,{"commercial-townhouse":True,"garden-townhouse":True})
        item=inspect(TARGET,PROJECT,Session(Response()),"2026-11-02T08:00:00+00:00")
        self.assertEqual(item["status"],"source-checked")
        self.assertTrue(all(x["source_verified"] for x in item["product_labels"]))
        self.assertEqual(item["published_prices"],0)

    def test_heading_and_phrase_must_be_on_source_page(self):
        invalid=T.replace("Izumi Gardenia","A Different Compound")
        found,status=evidence(invalid,TARGET)
        self.assertIsNone(found)
        self.assertEqual(status,"project-title-not-confirmed")
        missing=T.replace("garden townhouses","homes")
        found,status=evidence(missing,TARGET)
        self.assertFalse(found["garden-townhouse"])

    def test_partial_word_not_false_positive(self):
        self.assertFalse(has_phrase("A showtownhouse unit","townhouse"))
        self.assertTrue(has_phrase("Townhouse and Shophouse","townhouse"))

    def test_project_and_host_isolation(self):
        other={**TARGET,"source_url":"https://other.example/subproject"}
        row=inspect(other,PROJECT,Session(Response()),"2026-11-02T08:00:00+00:00")
        self.assertEqual(row["status"],"unapproved-source-host")

    def test_registry_all_approved_sources_and_no_numeric_offer_fields(self):
        projects={p["id"]:p for p in PROJECTS["data"]}
        self.assertGreaterEqual(len(CONFIG["sources"]),4)
        count=0
        for item in CONFIG["sources"]:
            self.assertTrue(permitted(item["source_url"],item["allowed_host"]))
            self.assertIn("landed",projects[item["project_id"]]["segment_ids"])
            for kind in item["product_types"]:
                self.assertTrue(kind["source_phrase"])
                self.assertFalse(any(field in kind for field in ("price","asp","vnd_per_m2")))
                count+=1
        self.assertGreaterEqual(count,9)

    def test_batch_result_zero_prices(self):
        result=run({"sources":[TARGET]}, {"data":[PROJECT]},Session(Response()),"2026-11-02T08:00:00+00:00")
        self.assertEqual(result["price_records_published"],0)
        self.assertEqual(result["sources_checked"],1)
        self.assertEqual(result["product_types_verified"],2)

if __name__=="__main__":
    unittest.main()
