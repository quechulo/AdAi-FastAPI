from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health, rag, mcp, agentic, saveChatHistory, viewAd
from app.core.logging import configure_logging
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
