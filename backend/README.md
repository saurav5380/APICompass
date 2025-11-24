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

## Local Connector ingest

Organizations can opt into “no keys on server” mode per connection. When `local_connector_enabled` is true, the backend issues a one-time agent token (`lc_…`) instead of storing the provider API key. The desktop agent keeps the real key in the OS keychain, polls the provider locally, and posts signed aggregates to `POST /ingest`.

- **Signature:** Compute `base64url(hmac_sha256(agent_token, raw_json_body))` and send it via `X-Agent-Signature`. The backend decrypts the stored agent token, verifies the signature, and rejects mismatched scopes or inactive connections.
- **Payload:** Include the connection UUID, provider, environment, agent version, and one or more usage samples—each sample mirrors the `UsageSample` dataclass (metric, unit, quantity, optional unit_cost/metadata, and timestamp).
- **Entitlements:** The ingest endpoint enforces the org’s sync interval, so agents should respect HTTP 429 responses before retrying.

Example:

```bash
curl https://api.local/ingest \
  -H "Content-Type: application/json" \
  -H "X-Agent-Signature: ${SIGNATURE}" \
  -d '{
    "connection_id": "9c6ac2f0-5b52-4a85-9d4c-e1f1a5f5d710",
    "provider": "openai",
    "environment": "prod",
    "agent_version": "local-connector/1.0.0",
    "samples": [
      {
        "metric": "openai:tokens",
        "unit": "token",
        "quantity": 128000,
        "unit_cost": "0.000002",
        "currency": "usd",
        "ts": "2024-05-24T12:00:00Z",
        "metadata": {"requests": 412}
      }
    ]
  }'
```

### Actionable tips

`GET /usage/tips?environment=prod` returns heuristic suggestions (model mix, duplicate prompts, SendGrid plan usage). Each tip explains why it surfaced and links to docs/blog posts so the dashboard “tips” cards stay in sync with the API.

### Security & data control

See `backend/SECURITY.md` for what we store, retention defaults, and subprocessors. Org admins can:

- Export their data via `GET /api/data/export` (CSV).
- Schedule deletion via `POST /api/data/delete` (processed asynchronously).
- Rely on audit logs for sensitive actions (connections, budgets, alerts sent).

### Plans & Stripe bootstrap

Entitlements map to Stripe products/prices. Run the helper to create/update the catalog (Pro ships with a 14-day trial):

```bash
cd backend
python -m api_compass.scripts.bootstrap_plans --currency usd
```

Expose the webhook at `/api/billing/webhook` and point Stripe to it (using the `STRIPE_WEBHOOK_SECRET`). The endpoint listens for subscription create/update/delete events and updates each org’s feature flags within a minute. A Celery task (`entitlements.expire_trials`) sweeps every five minutes to downgrade organizations whose trials ended without payment.

## Database migrations

Alembic manages the schema (including Timescale extensions and hypertables).

```bash
cd backend
alembic upgrade head
```

Set `DATABASE_URL` (for example, `postgresql+psycopg://postgres:postgres@localhost:15432/api_compass`) before running Alembic commands. Use `alembic revision --autogenerate -m "describe change"` when adding new models.
