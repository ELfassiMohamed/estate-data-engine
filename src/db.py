from __future__ import annotations

import json
import logging
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from src.config import settings
from src.models import Listing

logger = logging.getLogger(__name__)


class PostgresClient:
    def __init__(self) -> None:
        self.conn = psycopg.connect(
            host=settings.pghost,
            port=settings.pgport,
            dbname=settings.pgdatabase,
            user=settings.pguser,
            password=settings.pgpassword,
            autocommit=True,
        )

    def close(self) -> None:
        self.conn.close()

    def init_schema(self, schema_path: Path) -> None:
        sql = schema_path.read_text(encoding="utf-8")
        with self.conn.cursor() as cur:
            cur.execute(sql)
        logger.info("Database schema initialized.")

    def insert_listing(self, listing: Listing) -> None:
        query = """
            INSERT INTO listings (
                title, source, url, type_bien, city, price, surface, description,
                contact_info, date_publication, scraped_at, raw_payload
            )
            VALUES (
                %(title)s, %(source)s, %(url)s, %(type_bien)s, %(city)s, %(price)s, %(surface)s, %(description)s,
                %(contact_info)s, %(date_publication)s, %(scraped_at)s, %(raw_payload)s
            )
            ON CONFLICT (url) DO NOTHING;
        """
        payload = {
            "title": listing.title,
            "source": listing.source,
            "url": listing.url,
            "type_bien": listing.type_bien,
            "city": listing.city,
            "price": listing.price,
            "surface": listing.surface,
            "description": listing.description,
            "contact_info": listing.contact_info,
            "date_publication": listing.date_publication,
            "scraped_at": listing.scraped_at,
            "raw_payload": Jsonb(json.loads(json.dumps(listing.raw_payload, ensure_ascii=False))),
        }
        with self.conn.cursor() as cur:
            cur.execute(query, payload)
