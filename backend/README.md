# API Compass Backend

FastAPI service powering API Compass. It exposes authenticated REST/JSON endpoints, background tasks, and integrations with provider APIs and Stripe.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn api_compass.main:app --reload
```

The service relies on Postgres, Redis, and object storage. When running through Docker Compose (defined at the repo root), environment variables are provided automatically.

## Database migrations

Alembic manages the schema (including Timescale extensions and hypertables).

```bash
cd backend
alembic upgrade head
```

Set `DATABASE_URL` (for example, `postgresql+psycopg://postgres:postgres@localhost:5432/api_compass`) before running Alembic commands. Use `alembic revision --autogenerate -m "describe change"` when adding new models.
