from __future__ import annotations

import logging

from app.core.settings import Settings


def configure_logging(settings: Settings) -> None:
    level_name = (settings.log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    else:
        root_logger.setLevel(level)

    logging.getLogger("app").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
