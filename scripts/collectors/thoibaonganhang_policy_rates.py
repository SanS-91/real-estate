from __future__ import annotations
from .policy_news_common import parse_policy_news, discover_policy_news_url

SOURCE_ID = "banking-times-vn"


def parse_thoibaonganhang_policy_rates(html: str, source_url: str, fetched_at: str):
    return parse_policy_news(html, source_url, fetched_at, SOURCE_ID)


def discover_thoibaonganhang_policy_rates_url(html: str, landing_url: str):
    return discover_policy_news_url(html, landing_url, "thoibaonganhang.vn")
