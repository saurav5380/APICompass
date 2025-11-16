from fastapi import FastAPI

from api_compass.api.routes import router as api_router
from api_compass.core import telemetry
from api_compass.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time


def create_app() -> FastAPI:
    telemetry.setup_logging()
    telemetry.setup_sentry()

    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_and_trace_requests(request: Request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        telemetry.bind_request_context(request)
        response: Response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000
        telemetry.log_request(request, response.status_code, duration)
        return response

    app.include_router(api_router)

    return app


app = create_app()
