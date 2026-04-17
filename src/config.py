from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    pghost: str = os.getenv("PGHOST", "localhost")
    pgport: int = int(os.getenv("PGPORT", "5432"))
    pgdatabase: str = os.getenv("PGDATABASE", "realestate")
    pguser: str = os.getenv("PGUSER", "postgres")
    pgpassword: str = os.getenv("PGPASSWORD", "postgres")

    max_listing_pages: int = int(os.getenv("MAX_LISTING_PAGES", "3"))
    max_details_per_source: int = int(os.getenv("MAX_DETAILS_PER_SOURCE", "40"))
    headless: bool = os.getenv("HEADLESS", "true").lower() == "true"
    request_timeout_ms: int = int(os.getenv("REQUEST_TIMEOUT_MS", "45000"))

    # Seed URLs (you can tune these without touching scraper code).
    avito_start_urls: tuple[str, ...] = (
        "https://www.avito.ma/fr/maroc/appartements-%C3%A0_vendre",
    )
    mubawab_start_urls: tuple[str, ...] = (
        "https://www.mubawab.ma/fr/sc/appartements-a-vendre",
    )


settings = Settings()
