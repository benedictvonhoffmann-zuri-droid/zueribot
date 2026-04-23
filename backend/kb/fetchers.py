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

    def fetch_rendered(self, url: str) -> Optional[FetchResult]:
        """Playwright-rendered fetch — not yet implemented. See spec §12."""
        raise NotImplementedError(
            "Playwright fallback not wired yet. Add playwright to "
            "requirements and implement when the first stadt-zuerich.ch "
            "ingester lands."
        )
