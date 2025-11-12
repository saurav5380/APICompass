from fastapi import FastAPI

from api_compass.api.routes import health
from api_compass.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(health.router, prefix="/health", tags=["health"])

    return app


app = create_app()
