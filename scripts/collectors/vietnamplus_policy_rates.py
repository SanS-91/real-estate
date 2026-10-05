from __future__ import annotations
from .policy_news_common import parse_policy_news, discover_policy_news_url

SOURCE_ID = "vna-vietnamplus"


def parse_vietnamplus_policy_rates(html: str, source_url: str, fetched_at: str):
    return parse_policy_news(html, source_url, fetched_at, SOURCE_ID)


def discover_vietnamplus_policy_rates_url(html: str, landing_url: str):
    return discover_policy_news_url(html, landing_url, "vietnamplus.vn")
