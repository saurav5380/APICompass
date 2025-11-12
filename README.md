# API Compass

Monorepo scaffolding for API Compass, an API spend tracker for solo developers. The workspace currently contains:

- `frontend/` – Next.js 14 (App Router, TypeScript, Tailwind, shadcn-ready) dashboard.
- `backend/` – FastAPI 0.115 service with Pydantic Settings, SQLAlchemy/Alembic, and placeholders for provider connectors.
- `docker-compose.yml` – Development stack with TimescaleDB, Redis, frontend, and backend services.

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
docker compose up --build
```

The frontend will be available at http://localhost:3000 and the API at http://localhost:8000. Postgres (Timescale) listens on 5432 and Redis on 6379.

## Database & migrations

- Backend migrations: `cd backend && alembic upgrade head`
- Prisma client/schema (for Next.js server actions): `cd frontend && npm run prisma:generate`
- To validate the Prisma schema locally, set `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/api_compass`

