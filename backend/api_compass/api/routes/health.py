from fastapi import APIRouter

from api_compass.core.config import settings

router = APIRouter()


@router.get("/", summary="Liveness probe")
def read_health() -> dict[str, str]:
    return {"status": "ok", "service": settings.project_name}
