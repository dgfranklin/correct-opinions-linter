"""Fetch and parse the public Correct Opinions list."""

import asyncio
import html
import logging
import re

import aiohttp

OPINIONS_URL = "https://www.correctopinions.info/"

log = logging.getLogger(__name__)

_NOISE = {
    "Google Sites",
    "Report abuse",
    "Page details",
    "Page updated",
    "Embedded Files",
    "Skip to main content",
    "Skip to navigation",
    "Search this site",
    "Correct Opinions",
}


def parse_opinions(page_html: str) -> dict[int, str]:
    """Extract the numbered opinion list from the Google Sites HTML."""
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", page_html, flags=re.DOTALL)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL)
    raw_texts = re.findall(r">([^<]{10,})<", cleaned)

    opinions: dict[int, str] = {}
    capturing = False

    for raw in raw_texts:
        text = html.unescape(raw.strip())
        if not text:
            continue
        if text == "Correct Opinions":
            capturing = True
            continue
        if not capturing or text in _NOISE:
            continue
        if any(keyword in text for keyword in ("rgba", "font-", "function ", "var ", "//")):
            continue

        opinions[len(opinions) + 1] = text

    return opinions


class OpinionStore:
    """Concurrency-safe store for the current set of correct opinions."""

    def __init__(self) -> None:
        self.opinions: dict[int, str] = {}
        self._lock = asyncio.Lock()

    async def refresh(self) -> None:
        """Fetch opinions from the website and update the store."""
        log.info("Fetching correct opinions from %s ...", OPINIONS_URL)
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=30)
                async with session.get(OPINIONS_URL, timeout=timeout) as response:
                    response.raise_for_status()
                    page_html = await response.text()

            new_opinions = parse_opinions(page_html)
            if not new_opinions:
                log.warning("Parsed 0 opinions — keeping previous list")
                return

            async with self._lock:
                self.opinions = new_opinions

            log.info("Loaded %d correct opinions", len(new_opinions))
        except Exception as error:
            log.error("Failed to fetch opinions: %s", error)
            if not self.opinions:
                raise RuntimeError(
                    f"Could not load initial opinions from {OPINIONS_URL}: {error}"
                ) from error

    async def get_snapshot(self) -> dict[int, str]:
        """Return a copy of the current opinions."""
        async with self._lock:
            return dict(self.opinions)
