from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from datetime import datetime, timezone
import hashlib
import re
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



def fetch_html_segmented(
    url: str,
    timeout: int = 30,
    max_bytes: int = 15_000_000,
    segment_bytes: int = 1_000_000,
    segment_retries: int = 3,
    session: Optional[requests.Session] = None,
) -> FetchResult:
    """Fetch a large/fragile document in HTTP byte ranges.

    Some official document hosts close long-lived responses before the advertised
    Content-Length is fully delivered. Requests/urllib3 does not automatically
    retry after a partial response body. Fetching smaller byte ranges makes the
    transport restartable without weakening parser/evidence rules.

    If the server ignores Range requests, fall back to a small number of full
    identity-encoded GET attempts.
    """
    s = session or build_session()
    started = time.monotonic()
    seg = max(64 * 1024, int(segment_bytes))
    tries = max(1, int(segment_retries))
    headers = {"Range": f"bytes=0-{seg-1}", "Accept-Encoding": "identity", "Connection": "close"}

    probe = s.get(url, timeout=(10, timeout), headers=headers, allow_redirects=True)
    probe.raise_for_status()
    content_range = probe.headers.get("Content-Range") or ""
    m = re.match(r"bytes\s+(\d+)-(\d+)/(\d+|\*)", content_range, re.I)

    if probe.status_code != 206 or not m or m.group(3) == "*":
        last_exc = None
        for _ in range(tries):
            try:
                r = s.get(
                    url,
                    timeout=(10, timeout),
                    headers={"Accept-Encoding": "identity", "Connection": "close"},
                    allow_redirects=True,
                )
                r.raise_for_status()
                raw = r.content
                if len(raw) > max_bytes:
                    raise ValueError(f"Response exceeds max_bytes={max_bytes} for {url}")
                return _fetch_result_from_raw(r, raw, started)
            except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ContentDecodingError, requests.exceptions.ConnectionError) as exc:
                last_exc = exc
                time.sleep(0.5)
        if last_exc:
            raise last_exc
        raise ValueError(f"Unable to fetch {url}")

    total = int(m.group(3))
    if total > max_bytes:
        raise ValueError(f"Response exceeds max_bytes={max_bytes} for {url}: content-length={total}")

    first_start, first_end = int(m.group(1)), int(m.group(2))
    if first_start != 0:
        raise ValueError(f"Unexpected initial Content-Range for {url}: {content_range}")
    first = probe.content
    expected_first = first_end - first_start + 1
    if len(first) != expected_first:
        raise ValueError(f"Initial range length mismatch for {url}: got {len(first)}, expected {expected_first}")

    chunks = [first]
    pos = first_end + 1
    final_response = probe
    final_url = probe.url

    while pos < total:
        end = min(pos + seg - 1, total - 1)
        last_exc = None
        chunk = None
        for _ in range(tries):
            try:
                rr = s.get(
                    final_url,
                    timeout=(10, timeout),
                    headers={"Range": f"bytes={pos}-{end}", "Accept-Encoding": "identity", "Connection": "close"},
                    allow_redirects=True,
                )
                rr.raise_for_status()
                cr = rr.headers.get("Content-Range") or ""
                mm = re.match(r"bytes\s+(\d+)-(\d+)/(\d+|\*)", cr, re.I)
                if rr.status_code != 206 or not mm:
                    raise ValueError(f"Range fetch not honored for {final_url}: status={rr.status_code}, content-range={cr!r}")
                got_start, got_end = int(mm.group(1)), int(mm.group(2))
                if got_start != pos or got_end != end:
                    raise ValueError(f"Unexpected Content-Range for {final_url}: {cr}; expected bytes {pos}-{end}/{total}")
                payload = rr.content
                expected = end - pos + 1
                if len(payload) != expected:
                    raise ValueError(f"Range length mismatch for {final_url}: got {len(payload)}, expected {expected}")
                chunk = payload
                final_response = rr
                break
            except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ContentDecodingError, requests.exceptions.ConnectionError) as exc:
                last_exc = exc
                time.sleep(0.5)
        if chunk is None:
            if last_exc:
                raise last_exc
            raise ValueError(f"Unable to fetch range {pos}-{end} for {final_url}")
        chunks.append(chunk)
        pos = end + 1

    raw = b"".join(chunks)
    if len(raw) != total:
        raise ValueError(f"Segmented fetch length mismatch for {final_url}: got {len(raw)}, expected {total}")
    # Use final response metadata but preserve the first resolved URL if later
    # range responses do not redirect identically.
    final_response.url = final_url
    return _fetch_result_from_raw(final_response, raw, started)


def _fetch_result_from_raw(r, raw: bytes, started: float) -> FetchResult:
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
        enc = getattr(r, "encoding", None) or getattr(r, "apparent_encoding", None) or "utf-8"
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
