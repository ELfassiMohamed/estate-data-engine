from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"\s+", " ", value).strip()
    return text or None


def parse_decimal(value: str | int | float | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    normalized = re.sub(r"[^\d,.\-]", "", str(value))
    if not normalized:
        return None

    if normalized.count(",") > 0 and normalized.count(".") == 0:
        normalized = normalized.replace(",", ".")
    elif normalized.count(",") > 0 and normalized.count(".") > 0:
        normalized = normalized.replace(",", "")

    try:
        val = Decimal(normalized)
        # Sanity check: If price is > 100 Billion, it's likely a phone number or ID error
        if val > 100_000_000_000:
            return None
        return val
    except InvalidOperation:
        return None


def parse_surface_from_text(text: str | None) -> Decimal | None:
    if not text:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|m)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return parse_decimal(match.group(1))


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_json_ld_blocks(raw_scripts: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for raw in raw_scripts:
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            blocks.extend(item for item in parsed if isinstance(item, dict))
        elif isinstance(parsed, dict):
            blocks.append(parsed)
    return blocks


def find_first_value(data: dict[str, Any], candidates: list[str]) -> Any:
    for key in candidates:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def extract_contact_text_from_html(html: str) -> str | None:
    matches = re.findall(r"(?:\+212|0)\s*\d(?:[\s.-]?\d){7,}", html)
    unique = sorted({re.sub(r"\s+", "", phone) for phone in matches})
    if unique:
        return ", ".join(unique)
    return None
