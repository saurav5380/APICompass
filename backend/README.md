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

## Background workers

Celery powers the hourly provider polls. Run the worker and beat processes locally once the virtualenv is active:

```bash
celery -A api_compass.celery_app worker --loglevel=info
celery -A api_compass.celery_app beat --loglevel=info
```

The Docker Compose file exposes matching services (`celery_worker` and `celery_beat`) so `docker compose up celery_worker celery_beat` keeps the scheduler and worker online alongside Redis.

### Usage aggregates

Usage dashboards read from the `daily_usage_costs` aggregate table. To backfill the last 45 days on demand, run:

```bash
celery -A api_compass.celery_app call usage.refresh_daily_usage_costs
```

You can pass a custom day window via `--args='[30]'`.

### Alerts & digests

Celery manages alert evaluations (`alerts.evaluate`) every 15 minutes and daily usage digests (`alerts.daily_digest`). Configure recipients through `ALERTS_DEFAULT_RECIPIENT` and quiet hours via `ALERTS_QUIET_HOURS_*`. To run the sweep manually:

```bash
celery -A api_compass.celery_app call alerts.evaluate
celery -A api_compass.celery_app call alerts.daily_digest
```

### Actionable tips

`GET /usage/tips?environment=prod` returns heuristic suggestions (model mix, duplicate prompts, SendGrid plan usage). Each tip explains why it surfaced and links to docs/blog posts so the dashboard “tips” cards stay in sync with the API.

## Database migrations

Alembic manages the schema (including Timescale extensions and hypertables).

```bash
cd backend
alembic upgrade head
```

Set `DATABASE_URL` (for example, `postgresql+psycopg://postgres:postgres@localhost:15432/api_compass`) before running Alembic commands. Use `alembic revision --autogenerate -m "describe change"` when adding new models.
