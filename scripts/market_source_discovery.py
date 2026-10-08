"""Discover news article links from a publisher's own news index.

Only same-host /tin-tuc/<slug>/ URLs are eligible. Discovery does not assert
publication date, metrics, or source freshness; those require article-level checks.
"""
from __future__ import annotations

import hashlib
from urllib.parse import urljoin, urlsplit, urlunsplit
from bs4 import BeautifulSoup


def discover_namlong_links(html: str, index_url: str, max_items: int = 12) -> list[str]:
    root = urlsplit(index_url)
    origin_host = (root.hostname or "").lower().removeprefix("www.")
    found = []
    seen = set()
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        absolute = urlsplit(urljoin(index_url, href))
        host = (absolute.hostname or "").lower().removeprefix("www.")
        if absolute.scheme not in ("http", "https") or host != origin_host:
            continue
        parts = [p for p in absolute.path.strip("/").split("/") if p]
        if len(parts) != 2 or parts[0] != "tin-tuc":
            continue
        if not all(c.isascii() and (c.islower() or c.isdigit() or c == "-") for c in parts[1]):
            continue
        url = urlunsplit(("https", root.netloc, "/" + "/".join(parts) + "/", "", ""))
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
        if len(found) >= max_items:
            break
    return found


def namlong_target(url: str, index_url: str) -> dict:
    suffix = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return {
        "target_id": "nam-long-discovered-" + suffix,
        "source_id": "developer-official",
        "observation_source_id": "nam-long-official",
        "url": url,
        "period": None,
        "period_type": "date",
        "scope": "developer-project-updates",
        "collector": "namlong_official",
        "enabled": True,
        "auto_discovered": True,
        "discovery_url": index_url,
    }


def discover_cbre_hcmc_reports(html: str, index_url: str, max_items: int = 8) -> list[dict]:
    """Find HCMC quarterly Figures reports from CBRE's official insight index."""
    import re
    root = urlsplit(index_url)
    host = (root.hostname or "").lower().removeprefix("www.")
    soup = BeautifulSoup(html, "lxml")
    found = []
    seen = set()
    for a in soup.select("a[href]"):
        full = urlsplit(urljoin(index_url, a.get("href", "").strip()))
        if full.scheme not in ("https", "http") or (full.hostname or "").lower().removeprefix("www.") != host:
            continue
        path = full.path.rstrip("/")
        if not path.startswith("/insights/figures/"):
            continue
        slug = path.rsplit("/", 1)[-1].lower()
        if not slug.startswith("ho-chi-minh-city-figures-"):
            continue
        match = re.search(r"(?:^|-)q([1-4])-(20\d{2})(?:$|-)", slug)
        if not match:
            continue
        period = f"{match.group(2)}-Q{match.group(1)}"
        url = urlunsplit(("https", root.netloc, path, "", ""))
        if url in seen:
            continue
        seen.add(url)
        found.append({
            "target_id": "cbre-discovered-" + hashlib.sha256(url.encode()).hexdigest()[:16],
            "source_id": "cbre-vietnam",
            "observation_source_id": "cbre-vietnam-market",
            "url": url,
            "period": period,
            "period_type": "quarter",
            "scope": "hcmc-residential",
            "collector": "cbre_market",
            "enabled": True,
            "auto_discovered": True,
            "discovery_url": index_url,
        })
        if len(found) >= max_items:
            break
    return found
