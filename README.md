# API Compass

Monorepo scaffolding for API Compass, an API spend tracker for solo developers. The workspace currently contains:

- `frontend/` – Next.js 14 (App Router, TypeScript, Tailwind, shadcn-ready) dashboard.
- `backend/` – FastAPI 0.115 service with Pydantic Settings, SQLAlchemy/Alembic, and placeholders for provider connectors.
- `compose.dev.yml` / `compose.prod.yml` – Docker Compose definitions for development and production (the legacy `docker-compose.yml` points to the dev stack for backward-compatibility).

## Prerequisites

- Node.js 20+
- Python 3.11+
- Docker (for Compose-based dev)

## Local development (without Docker)

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn api_compass.main:app --reload
```

## Docker-based workflow

```bash
docker compose -f compose.dev.yml up --build
```

The frontend will be available at http://localhost:3000 and the API at http://localhost:8000. Postgres (Timescale) listens on 5432 and Redis on 6379. For production deployments use `compose.prod.yml` with pre-built images and real secrets loaded via `backend/.env.prod` and `frontend/.env.prod`.

## Database & migrations

- Backend migrations: `cd backend && alembic upgrade head`
- Prisma client/schema (for Next.js server actions): `cd frontend && npm run prisma:generate`
- To validate the Prisma schema locally, set `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/api_compass`

## CI/CD & releases

- GitHub Actions (`.github/workflows/ci.yml`) lints, runs Alembic migrations/tests, and builds Docker images on every push/PR.
- Follow `RELEASE.md` for the full release playbook, rollback steps, and smoke-test checklist (connect the test provider → confirm forecasts render).
