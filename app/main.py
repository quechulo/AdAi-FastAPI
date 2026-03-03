from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import chat, health, rag, mcp, agentic, saveChatHistory, viewAd
from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.db.session import get_db_session

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown tasks."""
    settings = get_settings()

    # Startup
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info(f"CORS Origins: {settings.cors_origins}")

    # Test database connectivity
    try:
        with next(get_db_session()) as session:
            session.execute(text("SELECT 1"))
            logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.warning(
            "Application will continue but database operations may fail"
        )

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # Parse CORS origins from comma-separated string
    cors_origins = [
        origin.strip() for origin in settings.cors_origins.split(",")
    ]

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(rag.router, prefix="/api/v1")
    app.include_router(mcp.router, prefix="/api/v1")
    app.include_router(agentic.router, prefix="/api/v1")
    app.include_router(saveChatHistory.router, prefix="/api/v1")
    app.include_router(viewAd.router, prefix="/api/v1")
    app.include_router(health.router)

    return app


app = create_app()
