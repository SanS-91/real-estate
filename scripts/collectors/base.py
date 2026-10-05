from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from datetime import datetime, timezone
import hashlib
import time
from typing import Optional
import requests
from pypdf import PdfReader
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi,en;q=0.8",
}

@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    fetched_at: str
    content_hash: str
    content_type: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    elapsed_ms: int | None = None


def build_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def fetch_html(
    url: str,
    timeout: int = 30,
    max_bytes: int = 5_000_000,
    session: Optional[requests.Session] = None,
) -> FetchResult:
    s = session or build_session()
    started = time.monotonic()
    with s.get(url, timeout=(10, timeout), stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"Response exceeds max_bytes={max_bytes} for {url}")
            chunks.append(chunk)
        raw = b"".join(chunks)
        content_type = (r.headers.get("Content-Type") or "").lower()
        is_pdf = "application/pdf" in content_type or r.url.lower().split("?", 1)[0].endswith(".pdf")
        if is_pdf:
            try:
                reader = PdfReader(BytesIO(raw))
                text = "\n".join((page.extract_text() or "") for page in reader.pages)
                if not text.strip():
                    raise ValueError("PDF text extraction returned empty content")
            except Exception as exc:
                raise ValueError(f"Unable to extract PDF text from {r.url}: {exc}") from exc
        else:
            enc = r.encoding or r.apparent_encoding or "utf-8"
            text = raw.decode(enc, errors="replace")
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return FetchResult(
            url=r.url,
            status_code=r.status_code,
            text=text,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            content_hash=hashlib.sha256(raw).hexdigest(),
            content_type=r.headers.get("Content-Type"),
            etag=r.headers.get("ETag"),
            last_modified=r.headers.get("Last-Modified"),
            elapsed_ms=elapsed_ms,
        )
