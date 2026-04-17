from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.config import settings
from src.models import Listing
from src.utils.retry import with_retry

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    source_name: str

    def __init__(self, start_urls: tuple[str, ...]) -> None:
        self.start_urls = start_urls
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None

    async def __aenter__(self) -> "BaseScraper":
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(headless=settings.headless)
        self.context = await self.browser.new_context(
            locale="fr-MA",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        await self._playwright.stop()

    @abstractmethod
    def is_detail_url(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def parse_listing(self, page: Page, url: str) -> Listing:
        raise NotImplementedError

    async def goto_with_retry(self, page: Page, url: str) -> None:
        async def _task() -> None:
            await page.goto(url, timeout=settings.request_timeout_ms, wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(700, 1300))

        await with_retry(_task, retries=3, delay_seconds=1.2, backoff=2.0)

    async def extract_urls_from_page(self, page: Page, base_url: str) -> list[str]:
        hrefs = await page.eval_on_selector_all(
            "a[href]",
            "elements => elements.map(e => e.getAttribute('href'))",
        )
        urls: list[str] = []
        for href in hrefs:
            if not href:
                continue
            absolute = urljoin(base_url, href)
            cleaned = absolute.split("#")[0]
            if self.is_detail_url(cleaned):
                urls.append(cleaned)
        return sorted(set(urls))

    async def collect_listing_urls(self) -> list[str]:
        assert self.context is not None
        discovered: set[str] = set()

        for start_url in self.start_urls:
            page = await self.context.new_page()
            try:
                await self.goto_with_retry(page, start_url)
                for page_idx in range(1, settings.max_listing_pages + 1):
                    found = await self.extract_urls_from_page(page, page.url)
                    discovered.update(found)
                    logger.info(
                        "[%s] Listing page %s/%s: found %s candidate URLs",
                        self.source_name,
                        page_idx,
                        settings.max_listing_pages,
                        len(found),
                    )

                    if page_idx >= settings.max_listing_pages:
                        break

                    next_clicked = await self.try_next_page(page)
                    if not next_clicked:
                        logger.info("[%s] No next page button found. Stop pagination.", self.source_name)
                        break
            finally:
                await page.close()

        return list(discovered)

    async def try_next_page(self, page: Page) -> bool:
        next_selectors = [
            "a[rel='next']",
            "a[aria-label*='Suiv']",
            "button[aria-label*='Suiv']",
            "a:has-text('Suivant')",
            "a:has-text('Next')",
        ]
        for selector in next_selectors:
            element = page.locator(selector).first
            if await element.count() == 0:
                continue
            try:
                await element.click(timeout=4000)
                await page.wait_for_timeout(1200)
                return True
            except Exception:  # noqa: BLE001 - selector might not be interactable.
                continue
        return False

    async def scrape(self) -> list[Listing]:
        assert self.context is not None
        all_urls = await self.collect_listing_urls()
        if not all_urls:
            logger.warning("[%s] No listing URLs discovered.", self.source_name)
            return []

        capped_urls = all_urls[: settings.max_details_per_source]
        logger.info(
            "[%s] Visiting %s listing detail URLs (cap=%s).",
            self.source_name,
            len(capped_urls),
            settings.max_details_per_source,
        )

        listings: list[Listing] = []
        for idx, url in enumerate(capped_urls, start=1):
            page = await self.context.new_page()
            try:
                await self.goto_with_retry(page, url)
                listing = await self.parse_listing(page, url)
                listings.append(listing)
                logger.info("[%s] Parsed listing %s/%s", self.source_name, idx, len(capped_urls))
            except Exception as exc:  # noqa: BLE001 - we skip failed pages in PoC.
                logger.exception("[%s] Failed to parse %s: %s", self.source_name, url, exc)
            finally:
                await page.close()
                await asyncio.sleep(random.uniform(0.6, 1.2))

        return listings

    @staticmethod
    def get_hostname(url: str) -> str:
        return urlparse(url).netloc.lower()
