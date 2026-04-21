from __future__ import annotations

import logging
from pathlib import Path

from src.config import settings
from src.db import PostgresClient
from src.models import Listing
from src.scrapers.avito import AvitoScraper
from src.scrapers.mubawab import MubawabScraper

logger = logging.getLogger(__name__)


async def run_pipeline() -> None:
    db = PostgresClient()
    schema_path = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
    db.init_schema(schema_path)

    all_listings: list[Listing] = []
    try:
        async with AvitoScraper(start_urls=settings.avito_start_urls) as avito:
            avito_items = await avito.scrape()
            all_listings.extend(avito_items)
            logger.info("[avito] Extracted %s listings.", len(avito_items))

        async with MubawabScraper(start_urls=settings.mubawab_start_urls) as mubawab:
            mubawab_items = await mubawab.scrape()
            all_listings.extend(mubawab_items)
            logger.info("[mubawab] Extracted %s listings.", len(mubawab_items))

        for item in all_listings:
            try:
                db.insert_listing(item)
            except Exception as e:
                logger.error("Failed to insert listing %s: %s", item.url, e)
        logger.info("Inserted %s listings into PostgreSQL.", len(all_listings))
    finally:
        db.close()


async def run_pipeline_distributed() -> None:
    """
    Distributed pipeline: collect listing URLs, then enqueue each one
    as a Celery task for parallel scraping by workers.
    """
    from src.tasks import scrape_listing_task  # noqa: local import to avoid circular deps

    # Ensure schema exists before workers start inserting.
    db = PostgresClient()
    schema_path = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
    db.init_schema(schema_path)

    enqueued = 0

    # --- Avito ---
    async with AvitoScraper(start_urls=settings.avito_start_urls) as avito:
        avito_urls = await avito.collect_listing_urls()
        logger.info("[avito] Discovered %s listing URLs.", len(avito_urls))
        
        existing_avito = db.list_existing_urls(avito_urls)
        new_avito = [u for u in avito_urls if u not in existing_avito]
        logger.info("[avito] %s already in DB, enqueuing %s new URLs.", len(existing_avito), len(new_avito))

        for url in new_avito:
            scrape_listing_task.delay(url, "avito")
            enqueued += 1

    # --- Mubawab ---
    async with MubawabScraper(start_urls=settings.mubawab_start_urls) as mubawab:
        mubawab_urls = await mubawab.collect_listing_urls()
        logger.info("[mubawab] Discovered %s listing URLs.", len(mubawab_urls))

        existing_mubawab = db.list_existing_urls(mubawab_urls)
        new_mubawab = [u for u in mubawab_urls if u not in existing_mubawab]
        logger.info("[mubawab] %s already in DB, enqueuing %s new URLs.", len(existing_mubawab), len(new_mubawab))

        for url in new_mubawab:
            scrape_listing_task.delay(url, "mubawab")
            enqueued += 1

    db.close()
    logger.info("Enqueued %s total scraping tasks to Celery.", enqueued)
