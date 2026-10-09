from __future__ import annotations
import unittest
from datetime import datetime, timezone
from market_news_rss import feed_items, parse_date, canonical_url, classify, evaluate, normalized_title

NOW=datetime(2026,10,9,tzinfo=timezone.utc)
FEED={"id":"test","source_id":"vnexpress-real-estate","url":"https://vnexpress.net/rss/bat-dong-san.rss","host":"vnexpress.net","category":"real-estate","max_items":15}
XML="""<rss version="2.0"><channel><title>Real Estate</title>
<item><title>Giá bán căn hộ Izumi City tại TP HCM</title><link>https://vnexpress.net/tin-nha-dat-123.html?utm_source=rss</link>
<description><![CDATA[<p>Nam Long cập nhật dự án bất động sản.</p>]]></description>
<pubDate>Fri, 09 Oct 2026 07:00:00 +0700</pubDate></item>
<item><title>Diễn biến giá nhà đất tại TP HCM</title><link>https://vnexpress.net/tin-gia-nha-456.html</link>
<description>Cập nhật thị trường nhà ở</description>
<pubDate>Fri, 09 Oct 2026 06:30:00 +0700</pubDate></item>
</channel></rss>"""


class NewsRSSTests(unittest.TestCase):
    def test_parses_publisher_rss(self):
        a=feed_items(XML)
        self.assertEqual(len(a),2)
        self.assertEqual(a[0]["title"],"Giá bán căn hộ Izumi City tại TP HCM")

    def test_filters_external_urls(self):
        self.assertIsNone(canonical_url("https://attacker.net/post", "vnexpress.net"))
        self.assertEqual(canonical_url("https://www.vnexpress.net/a.html?utm_id=1", "vnexpress.net"),"https://vnexpress.net/a.html")

    def test_extracts_date_and_projects(self):
        item=feed_items(XML)[0]
        row,error=classify(item,FEED,{"izumi-city":{"izumi city"}},NOW,21)
        self.assertIsNone(error)
        self.assertEqual(row["project_ids"],["izumi-city"])
        self.assertEqual(row["developer_ids"],["nam-long"])
        self.assertEqual(row["source_id"],"vnexpress-real-estate")
        self.assertIn("2026-10-09",row["published_at"])
        self.assertEqual(row["summary"],"Nam Long cập nhật dự án bất động sản.")

    def test_duplicate_idempotence(self):
        cfg={"feeds":[FEED],"days_lookback":21,"max_new_per_run":20}
        batch, reports=evaluate(cfg,{"test":XML},[],[{"id":"izumi-city","name":"Izumi City"}],{"vnexpress-real-estate"},NOW)
        self.assertEqual(len(batch),2)
        again,_=evaluate(cfg,{"test":XML},batch,[{"id":"izumi-city","name":"Izumi City"}],{"vnexpress-real-estate"},NOW)
        self.assertEqual(again,[])
        self.assertEqual(reports[0]["new"],2)

    def test_filtered_investment_news(self):
        other=dict(FEED,category="filtered-investment")
        item={"title":"Tỷ giá ngân hàng sáng nay","description":"Thông tin đầu tư tiền tệ","link":"https://vnexpress.net/a.html","date":"Fri, 09 Oct 2026 07:00:00 +0700"}
        self.assertEqual(classify(item,other,{},NOW,21)[1],"not-property-market-news")

    def test_invalid_future_and_missing_date(self):
        self.assertIsNone(parse_date("Sat, 10 Oct 2026 23:00:00 +0700",NOW))
        self.assertIsNone(parse_date("",NOW))


if __name__=="__main__":
    unittest.main()
