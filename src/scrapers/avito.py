from __future__ import annotations

import logging
import re

from playwright.async_api import Page

from src.models import Listing
from src.scrapers.base import BaseScraper
from src.utils.parsing import (
    clean_text,
    extract_contact_text_from_html,
    extract_json_ld_blocks,
    find_first_value,
    parse_date,
    parse_decimal,
    parse_surface_from_text,
)

logger = logging.getLogger(__name__)


class AvitoScraper(BaseScraper):
    source_name = "avito"

    def is_detail_url(self, url: str) -> bool:
        # Avito detail pages usually end with ".ht m" and contain '/fr/'.
        return "avito.ma" in self.get_hostname(url) and "/fr/" in url and url.endswith(".htm")

    async def parse_listing(self, page: Page, url: str) -> Listing:
        title = clean_text(await self._first_text(page, ["h1", "meta[property='og:title']"]))
        description = clean_text(
            await self._first_text(page, ["[data-testid='ad_description']", "meta[name='description']"])
        )
        city = clean_text(await self._first_text(page, ["[data-testid='ad_location']", "li:has-text('Ville')"]))
        type_bien = clean_text(
            await self._first_text(page, ["[data-testid='ad_param_type de bien']", "li:has-text('Type de bien')"])
        )
        raw_price = await self._first_text(page, ["[data-testid='ad_price']", "span:has-text('DH')"])
        price = parse_decimal(raw_price)
        surface = parse_surface_from_text(await page.content())
        html = await page.content()
        contact_info = extract_contact_text_from_html(html)

        json_ld_scripts = await page.eval_on_selector_all(
            "script[type='application/ld+json']",
            "els => els.map(e => e.textContent || '')",
        )
        json_ld_blocks = extract_json_ld_blocks(json_ld_scripts)
        date_publication = None
        for block in json_ld_blocks:
            date_value = find_first_value(block, ["datePosted", "datePublished", "uploadDate"])
            date_publication = parse_date(str(date_value)) if date_value else None
            if date_publication:
                break

        if not city:
            city = self._extract_city_from_url(url)

        return Listing(
            title=title,
            source=self.source_name,
            url=url,
            type_bien=type_bien,
            city=city,
            price=price,
            surface=surface,
            description=description,
            contact_info=contact_info,
            date_publication=date_publication,
            raw_payload={
                "json_ld": json_ld_blocks,
                "raw_price": raw_price,
            },
        )

    async def _first_text(self, page: Page, selectors: list[str]) -> str | None:
        for selector in selectors:
            loc = page.locator(selector).first
            if await loc.count() == 0:
                continue
            if selector.startswith("meta"):
                content = await loc.get_attribute("content")
                if content:
                    return content
                continue
            text = await loc.text_content()
            if text:
                return text
        return None

    @staticmethod
    def _extract_city_from_url(url: str) -> str | None:
        # ex: /fr/casablanca/... -> "casablanca"
        match = re.search(r"/fr/([^/]+)/", url)
        if not match:
            return None
        return clean_text(match.group(1).replace("-", " "))
