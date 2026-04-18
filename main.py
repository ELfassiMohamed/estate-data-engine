from __future__ import annotations

import argparse
import asyncio
import logging

from src.utils.logger import configure_logging


def main() -> None:
    configure_logging()
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Estate Data Engine")
    parser.add_argument(
        "--mode",
        choices=["sequential", "distributed"],
        default="sequential",
        help="sequential = original pipeline (default); distributed = Celery task queue",
    )
    args = parser.parse_args()

    try:
        if args.mode == "distributed":
            from src.pipeline import run_pipeline_distributed

            log.info("Starting DISTRIBUTED pipeline (Celery + Redis).")
            asyncio.run(run_pipeline_distributed())
        else:
            from src.pipeline import run_pipeline

            log.info("Starting SEQUENTIAL pipeline.")
            asyncio.run(run_pipeline())
    except KeyboardInterrupt:
        log.warning("Interrupted by user.")


if __name__ == "__main__":
    main()

