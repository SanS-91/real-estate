"""RSS-only, append-only Market news ingestion.

Publisher RSS metadata is evidence for links, dates and titles, not for any
numerical real-estate observation. Preserve provenance; never republish articles.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/market-news-feeds.json"
ARTICLES = ROOT / "data/mock/articles/articles.json"
PROJECTS = ROOT / "data/mock/market/projects.json"
SOURCES = ROOT / "data/mock/core/sources.json"
REPORT = ROOT / "data/candidate/market/market-news-rss-report.json"
HEADERS = {"User-Agent": "MarketIntelligenceRSS/1.0 (personal noncommercial feed reader)"}
MARKET_WORDS = ("bat dong san", "nha dat", "du an", "chung cu", "can ho", "nha o", "khu do thi", "gia nha", "gia dat", "dat nen", "quy hoach", "phap ly dat dai", "ha tang do thi", "chu dau tu", "bat dong san cong nghiep")
TOPIC_PATTERNS = {
    "supply": ("nguon cung", "mo ban", "ra mat", "phat trien du an"),
    "pricing": ("gia ban", "gia can ho", "gia nha", "gia dat", "bang gia dat"),
    "sales": ("doanh so", "giao dich", "tieu thu", "hap thu", "ban duoc"),
    "legal": ("phap ly", "so hong", "luat dat dai", "quy hoach"),
    "infrastructure": ("ha tang", "metro", "cao toc", "duong vanh dai", "san bay"),
}
DEV_PATTERNS = {
    "nam-long": ("nam long",),
    "khang-dien": ("khang dien",),
    "vinhomes": ("vinhomes", "vingroup"),
    "masterise": ("masterise",),
    "gamuda-land": ("gamuda",),
    "dat-xanh": ("dat xanh",),
}
MODULE_PATTERNS = {
    "legal": ("luat dat dai", "nghi dinh", "thong tu", "chinh sach nha o", "phap ly du an", "quy hoach su dung dat", "so hong", "bang gia dat", "tien su dung dat", "cap giay chung nhan"),
    "infrastructure": ("vanh dai", "cao toc", "metro", "san bay", "cau duong", "duong sat", "giai phong mat bang", "khoi cong", "thong xe", "ha tang giao thong"),
    "macro": ("lai suat", "ty gia", "gia vang", "cpi", "lam phat", "tang truong tin dung", "cung tien", "ngan hang nha nuoc", "gdp", "tang truong kinh te"),
}
MODULE_FEED_FILTERS = {
    "filtered-economy": ("macro", "market", "legal"),
    "filtered-policy-infrastructure": ("infrastructure", "legal", "market"),
    "filtered-property-legal": ("legal",),
}
REGION_PATTERNS = {
    "hcmc": ("tp hcm", "tp.hcm", "tphcm", "ho chi minh", "sai gon", "thu duc"),
    "dong-nai": ("dong nai",),
    "long-an": ("long an",),
    "binh-duong": ("binh duong",),
    "ha-noi": ("ha noi",),
}

def fold(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")

def clean_text(raw, limit=400):
    value = " ".join(BeautifulSoup(html.unescape(raw or ""), "html.parser").stripped_strings)
    return re.sub(r"\s+", " ", value).strip()[:limit]

def canonical_url(raw, expected_host):
    p = urlsplit((raw or "").strip())
    host = (p.hostname or "").lower().removeprefix("www.")
    if p.scheme not in ("http", "https") or host != expected_host or not p.path.strip("/"):
        return None
    return urlunsplit(("https", host, p.path.rstrip("/"), "", ""))

def feed_items(xml_text):
    root = ET.fromstring(xml_text)
    if root.tag not in ("rss", "rdf:RDF", "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF") and not root.tag.endswith("}rss"):
        raise ValueError("RSS XML root not recognized")
    channel = root.find("channel")
    if channel is None:
        channel = root
    out = []
    for item in channel.findall("item"):
        out.append({
            "title": item.findtext("title") or "",
            "link": item.findtext("link") or "",
            "description": item.findtext("description") or "",
            "date": item.findtext("pubDate") or "",
        })
    return out

def parse_date(raw, now):
    try:
        value = parsedate_to_datetime(raw)
        if value.tzinfo is None:
            return None
        value = value.astimezone(timezone.utc)
        if value > now + timedelta(hours=2) or value.year < 2020:
            return None
        return value
    except (ValueError, TypeError, IndexError, OverflowError):
        return None

def tags_for(text):
    folded = fold(text)
    return [tag for tag, variants in TOPIC_PATTERNS.items() if any(v in folded for v in variants)]

def classify(item, feed, project_names, now, days_lookback):
    title = clean_text(item.get("title"), 240)
    desc = clean_text(item.get("description"), 300)
    url = canonical_url(item.get("link"), feed["host"])
    dt = parse_date(item.get("date"), now)
    if not url or len(title) < 12 or dt is None:
        return None, "invalid-link-title-or-date"
    if dt < now - timedelta(days=days_lookback):
        return None, "older-than-retention-window"
    text = fold(title + " " + desc)
    if feed["category"] == "filtered-investment" and not any(x in text for x in MARKET_WORDS):
        return None, "not-property-market-news"
    module_ids = [module for module, patterns in MODULE_PATTERNS.items() if any(v in text for v in patterns)]
    property_relevant = any(v in text for v in MARKET_WORDS)
    if property_relevant:
        module_ids.insert(0, "market")
    if feed["category"] in MODULE_FEED_FILTERS and not any(module in MODULE_FEED_FILTERS[feed["category"]] for module in module_ids):
        return None, "off-topic-for-feed"
    if feed["category"] == "filtered-property-legal" and not ("legal" in module_ids and property_relevant):
        return None, "off-topic-for-feed"
    project_ids = [project_id for project_id, names in project_names.items() if any(v in text for v in names)]
    developer_ids = [did for did, variants in DEV_PATTERNS.items() if any(v in text for v in variants)]
    region_ids = [region for region, variants in REGION_PATTERNS.items() if any(v in text for v in variants)]
    tags = tags_for(title + " " + desc)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    article = {
        "id": "article-market-rss-" + digest,
        "title": title,
        "url": url,
        "category": "market" if "market" in module_ids or feed["category"] == "real-estate" else module_ids[0],
        "module_ids": list(dict.fromkeys(module_ids or (["market"] if feed["category"] == "real-estate" else []))),
        "subcategory": "news",
        "content_type": "publisher-rss",
        "published_at": dt.isoformat(),
        "source_id": feed["source_id"],
        "region_ids": region_ids,
        "project_ids": project_ids,
        "developer_ids": developer_ids,
        "tags": tags,
        "importance": 2,
        "summary": desc or title,
        "source_verification": {
            "method": "official-rss",
            "feed_url": feed["url"],
            "publisher_host": feed["host"],
            "publication_date_from_feed": True
        }
    }
    return article, None

def normalized_title(value):
    return re.sub(r"[^a-z0-9 ]", "", fold(value)).strip()

def evaluate(cfg, feeds, existing, projects, known_sources, now):
    project_names = {}
    for p in projects:
        variants = set()
        for value in (p.get("name"), p.get("id")):
            if value and len(fold(value)) >= 5:
                variants.add(fold(value).replace("-", " "))
        project_names[p["id"]] = variants
    known_urls = {url for x in existing if (url := canonical_url(x.get("url"), (urlsplit(x.get("url") or "").hostname or "").lower().removeprefix("www.")))}
    recent_titles = {normalized_title(x.get("title")) for x in existing}
    seen_urls = set()
    additions, source_reports = [], []
    for feed in cfg["feeds"]:
        if feed["source_id"] not in known_sources:
            source_reports.append({"source_id":feed["source_id"],"status":"unknown-source"}); continue
        if feed["id"] not in feeds:
            source_reports.append({"source_id":feed["source_id"],"status":"fetch-error"}); continue
        accepted = skipped = 0
        try:
            items = feed_items(feeds[feed["id"]])[:feed.get("max_items", 30)]
        except (ValueError, ET.ParseError):
            source_reports.append({"source_id":feed["source_id"],"status":"invalid-rss"}); continue
        for item in items:
            row, reason = classify(item, feed, project_names, now, cfg.get("days_lookback",21))
            if not row:
                skipped += 1
                continue
            key = normalized_title(row["title"])
            if row["url"] in known_urls or row["url"] in seen_urls or key in recent_titles:
                skipped += 1
                continue
            additions.append(row)
            seen_urls.add(row["url"])
            recent_titles.add(key)
            accepted += 1
        source_reports.append({"source_id":feed["source_id"],"status":"parsed","feed_items":len(items),"new":accepted,"skipped":skipped})
    additions.sort(key=lambda x:(x["published_at"],x["id"]),reverse=True)
    additions=additions[:cfg.get("max_new_per_run",75)]
    return additions, source_reports

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("preview","promote"), default="preview")
    args = ap.parse_args()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    payload = json.loads(ARTICLES.read_text(encoding="utf-8"))
    sources = {x["id"] for x in json.loads(SOURCES.read_text(encoding="utf-8")).get("data",[])}
    projects = json.loads(PROJECTS.read_text(encoding="utf-8")).get("data",[])
    snapshots = {}
    fetch_errors=[]
    for feed in cfg["feeds"]:
        try:
            response = requests.get(feed["url"], headers=HEADERS, timeout=25)
            response.raise_for_status()
            if len(response.content) > 2000000:
                raise ValueError("RSS exceeds size limit")
            snapshots[feed["id"]] = response.content.decode("utf-8-sig", errors="replace")
        except (requests.RequestException, ValueError) as exc:
            fetch_errors.append({"source_id":feed["source_id"],"error":type(exc).__name__})
    now = datetime.now(timezone.utc)
    candidates, checked = evaluate(cfg, snapshots, payload["data"], projects, sources, now)
    report = {"schema_version":1,"checked_at":now.isoformat(),"mode":args.mode,
        "feed_count":len(cfg["feeds"]),"feeds_fetched":len(snapshots),"new_count":len(candidates),
        "production_written":False,"sources":checked,"fetch_errors":fetch_errors,
        "new_articles":[{"title":a["title"],"source_id":a["source_id"],"url":a["url"],"published_at":a["published_at"]} for a in candidates[:30]]}
    if args.mode == "promote" and candidates:
        payload["data"]=sorted(payload["data"]+candidates,key=lambda a:(a.get("published_at") or "",a.get("id") or ""),reverse=True)
        payload["record_count"]=len(payload["data"])
        payload["generated_at"]=now.isoformat()
        payload["build_id"]="market-news-rss-"+now.strftime("%Y%m%dT%H%M%SZ")
        ARTICLES.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        report["production_written"]=True
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
