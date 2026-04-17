from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class Listing:
    title: str | None
    source: str
    url: str
    type_bien: str | None = None
    city: str | None = None
    price: Decimal | None = None
    surface: Decimal | None = None
    description: str | None = None
    contact_info: str | None = None
    date_publication: datetime | None = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    raw_payload: dict[str, Any] = field(default_factory=dict)
