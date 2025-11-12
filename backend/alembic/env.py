from __future__ import annotations

import pathlib
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]


def _add_repo_paths() -> None:
    """Ensure alembic picks up project packages and the per-project virtualenv."""
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))

    candidate_venvs = [
        BASE_DIR / ".venv",
        BASE_DIR.parent / ".venv",
    ]
    for venv_path in candidate_venvs:
        if not venv_path.exists():
            continue
        site_packages = list((venv_path / "lib").glob("python*/site-packages"))
        # macOS/Linux virtualenv layout
        for path in site_packages:
            if path.is_dir() and (str(path) not in sys.path):
                sys.path.insert(0, str(path))
        # Windows layout fallback
        windows_site_packages = venv_path / "Lib" / "site-packages"
        if windows_site_packages.is_dir() and (str(windows_site_packages) not in sys.path):
            sys.path.insert(0, str(windows_site_packages))


_add_repo_paths()

from api_compass.core.config import settings  # noqa: E402
from api_compass.db.base import Base  # noqa: E402
import api_compass.models  # noqa: F401,E402

config = context.config
config.set_main_option("sqlalchemy.url", str(settings.database_url))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=str(settings.database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
