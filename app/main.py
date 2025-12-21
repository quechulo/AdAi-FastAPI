from fastapi import FastAPI

from app.api import chat, health
from app.core.logging import configure_logging
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name)

    app.include_router(chat.router, prefix="/api/v1")

    app.include_router(health.router)

    return app


app = create_app()