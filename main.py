from __future__ import annotations

import asyncio
import logging

from src.pipeline import run_pipeline
from src.utils.logger import configure_logging


def main() -> None:
    configure_logging()
    try:
        asyncio.run(run_pipeline())
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("Interrupted by user.")


if __name__ == "__main__":
    main()
