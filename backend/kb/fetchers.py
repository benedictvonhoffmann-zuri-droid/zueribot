"""HTTP fetcher with per-domain rate limiting.

Playwright fallback for JS-heavy sites (stadt-zuerich.ch and friends)
is declared in the API but not yet implemented — spec §12. When the
first ingester that needs it lands, add playwright to requirements and
fill in ``fetch_rendered``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger("zuribot.kb.fetchers")

DEFAULT_UA = (
    "Mozilla/5.0 (compatible; BuenzliBot/0.1; +https://buenzli.space/bot) "
    "KB-ingest"
)


@dataclass
class FetchResult:
    url: str
    status_code: int
    content: bytes
    content_type: str
    final_url: str  # after redirects


class Fetcher:
    """Per-domain rate-limited HTTP client. One instance per ingest run."""

    def __init__(
        self,
        rate_limit_seconds: float = 1.5,
        timeout: int = 15,
        user_agent: str = DEFAULT_UA,
    ):
        self.rate_limit = rate_limit_seconds
        self.timeout = timeout
        self._last_request: dict[str, float] = {}
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/pdf",
            "Accept-Language": "de,en;q=0.9",
        })
        # Lazily-started persistent Playwright browser. Reused across
        # fetch_rendered calls because launching Chromium costs ~3-5s.
        self._pw = None
        self._browser = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self) -> None:
        """Tear down the cached Playwright browser, if any."""
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None

    def fetch(self, url: str) -> Optional[FetchResult]:
        """GET ``url`` with per-domain throttling. Returns None on failure."""
        domain = urlparse(url).netloc
        last = self._last_request.get(domain, 0.0)
        elapsed = time.time() - last
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)

        try:
            resp = self._session.get(
                url, timeout=self.timeout, allow_redirects=True,
            )
        except requests.RequestException as e:
            logger.warning("fetch failed url=%s err=%s", url, e)
            self._last_request[domain] = time.time()
            return None

        self._last_request[domain] = time.time()
        return FetchResult(
            url=url,
            status_code=resp.status_code,
            content=resp.content,
            content_type=resp.headers.get("Content-Type", ""),
            final_url=resp.url,
        )

    def fetch_rendered(
        self,
        url: str,
        wait_until: str = "networkidle",
        wait_ms: int = 0,
    ) -> Optional[FetchResult]:
        """Fetch ``url`` with headless Chromium. Use for JS-rendered sites.

        Respects the same per-domain rate limit as ``fetch``. Returns the
        fully-rendered HTML as bytes in ``content`` with
        ``content_type='text/html; charset=utf-8'``.

        Lazy-imports playwright so ingesters that only need static HTTP
        don't pull in the heavy dep.
        """
        domain = urlparse(url).netloc
        last = self._last_request.get(domain, 0.0)
        elapsed = time.time() - last
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)

        if self._browser is None:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError as e:
                raise RuntimeError(
                    "playwright not installed — add to requirements-heavy.txt "
                    "and run `python -m playwright install chromium`"
                ) from e
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)

        # Use Chromium's default UA — some sites (e.g. ch.ch) serve 404
        # to identifiably-bot UAs even when rendered via a real browser.
        page = self._browser.new_page()
        try:
            resp = page.goto(url, wait_until=wait_until, timeout=self.timeout * 1000)
            if wait_ms:
                page.wait_for_timeout(wait_ms)
            html = page.content()
            status = resp.status if resp else 0
            final_url = page.url
            page.close()
        except Exception as e:
            try:
                page.close()
            except Exception:
                pass
            logger.warning("rendered fetch failed url=%s err=%s", url, e)
            self._last_request[domain] = time.time()
            return None

        self._last_request[domain] = time.time()
        return FetchResult(
            url=url,
            status_code=status,
            content=html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
            final_url=final_url,
        )
