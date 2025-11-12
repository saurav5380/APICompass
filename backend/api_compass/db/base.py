from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def include_models() -> None:  # pragma: no cover - import side effects only
    import api_compass.models  # noqa: F401
