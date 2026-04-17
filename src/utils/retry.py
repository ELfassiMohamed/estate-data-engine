from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def with_retry(
    task_factory: Callable[[], Awaitable[T]],
    retries: int = 3,
    delay_seconds: float = 1.0,
    backoff: float = 2.0,
) -> T:
    """
    Execute an async callable with exponential backoff.
    """
    last_exc: Exception | None = None
    wait = delay_seconds
    for attempt in range(1, retries + 1):
        try:
            return await task_factory()
        except Exception as exc:  # noqa: BLE001 - we want broad retry for scraper PoC.
            last_exc = exc
            if attempt == retries:
                break
            logger.warning("Attempt %s/%s failed: %s", attempt, retries, exc)
            await asyncio.sleep(wait)
            wait *= backoff
    assert last_exc is not None
    raise last_exc
