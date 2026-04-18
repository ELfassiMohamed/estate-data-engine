"""Celery tasks for distributed listing scraping."""
from __future__ import annotations

import asyncio
import logging
import random
import time

from src.celery_app import celery_app
from src.db import PostgresClient
from src.utils.logger import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scraper registry — maps source names to their scraper classes.
# Import lazily inside the task to avoid heavy imports at module level.
# ---------------------------------------------------------------------------
SCRAPER_CLASSES = {
    "avito": "src.scrapers.avito.AvitoScraper",
    "mubawab": "src.scrapers.mubawab.MubawabScraper",
}


def _import_scraper_class(dotted_path: str):
    """Dynamically import a scraper class from its dotted path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


async def _scrape_single_listing(url: str, source: str) -> dict:
    """
    Launch Playwright, navigate to *url*, parse the listing using the
    appropriate scraper, insert into PostgreSQL, and return a summary dict.
    """
    scraper_path = SCRAPER_CLASSES.get(source)
    if scraper_path is None:
        raise ValueError(f"Unknown source: {source!r}. Expected one of {list(SCRAPER_CLASSES)}")

    ScraperClass = _import_scraper_class(scraper_path)

    # We only need the scraper instance for its parse_listing() method and
    # the Playwright browser context it manages.  Pass empty start_urls
    # because we are not collecting URLs — we already have the target URL.
    async with ScraperClass(start_urls=()) as scraper:
        page = await scraper.context.new_page()
        try:
            await scraper.goto_with_retry(page, url)
            listing = await scraper.parse_listing(page, url)
        finally:
            await page.close()

    # Persist to PostgreSQL (reuse existing DB logic).
    db = PostgresClient()
    try:
        db.insert_listing(listing)
    finally:
        db.close()

    return {
        "url": url,
        "source": source,
        "title": listing.title,
        "city": listing.city,
    }


@celery_app.task(
    bind=True,
    name="src.tasks.scrape_listing_task",
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
)
def scrape_listing_task(self, url: str, source: str) -> dict:
    """
    Celery task: scrape a single listing page and store it in PostgreSQL.

    Parameters
    ----------
    url : str
        The full URL of the listing detail page.
    source : str
        Either ``"avito"`` or ``"mubawab"``.

    Returns
    -------
    dict
        A summary of the scraped listing (url, source, title, city).
    """
    task_id = self.request.id or "local"
    logger.info("[task:%s] START  source=%s url=%s", task_id, source, url)

    # Anti-scraping politeness: random delay before hitting the site.
    delay = random.uniform(1.0, 3.0)
    logger.debug("[task:%s] Sleeping %.1fs before request", task_id, delay)
    time.sleep(delay)

    try:
        result = asyncio.run(_scrape_single_listing(url, source))
        logger.info(
            "[task:%s] SUCCESS title=%r city=%r",
            task_id,
            result.get("title", ""),
            result.get("city", ""),
        )
        return result

    except Exception as exc:
        logger.error("[task:%s] FAILED url=%s error=%s", task_id, url, exc, exc_info=True)
        # Retry with exponential backoff (10s, 20s, 40s).
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))
