"""FastAPI application for the lightweight game scores service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import scores


def create_app() -> FastAPI:
    """Build the FastAPI app with CORS configuration from settings."""
    application = FastAPI(
        title="Game Scores API",
        version="1.0.0",
        description="Lightweight score submission and leaderboard service.",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    application.include_router(scores.router, prefix="/api/v1", tags=["scores"])

    @application.get("/health", tags=["health"], summary="Service health check")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
