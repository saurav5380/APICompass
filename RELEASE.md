# Release playbook

## Pre-flight
1. Ensure the `CI` workflow in GitHub Actions is green on the commit you intend to ship.
2. Review pending Alembic migrations (`backend/alembic`). CI already runs `alembic upgrade head`, but confirm they apply on staging.
3. Bump versions/notes as needed and commit.

## Tag & push
```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```
GitHub Actions will build/test images for the tag.

## Deploy with Docker Compose (prod)
```bash
cp backend/.env.prod.example backend/.env.prod  # edit with real secrets
cp frontend/.env.example frontend/.env.prod  # add any prod-only overrides
export BACKEND_IMAGE=ghcr.io/your-org/api-compass-backend:vX.Y.Z
export FRONTEND_IMAGE=ghcr.io/your-org/api-compass-frontend:vX.Y.Z
export DATABASE_URL=postgresql+psycopg://...
export REDIS_URL=redis://...
export NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
export POSTGRES_PASSWORD=...  # if using bundled db
export POSTGRES_USER=...
export POSTGRES_DB=...
docker compose -f compose.prod.yml pull
docker compose -f compose.prod.yml up -d --remove-orphans
docker compose -f compose.prod.yml exec backend alembic upgrade head
```

## Smoke test
1. Hit `https://app.yourdomain.com/healthz` – should return HTTP 200 with `status: ok`.
2. Sign in and connect the "test provider" org.
3. Confirm the dashboard renders a forecast (sample data toggle off).
4. Trigger a manual alert (if configured) and verify it lands.

## Rollback plan
1. Identify the previous good tag/version (e.g., `vX.Y.(Z-1)`).
2. Redeploy images:
   ```bash
   export BACKEND_IMAGE=ghcr.io/your-org/api-compass-backend:vX.Y.(Z-1)
   export FRONTEND_IMAGE=ghcr.io/your-org/api-compass-frontend:vX.Y.(Z-1)
   docker compose -f compose.prod.yml up -d
   ```
3. If the latest database migration is safe to roll back, run:
   ```bash
   docker compose -f compose.prod.yml exec backend alembic downgrade -1
   ```
   Only downgrade if the migration is reversible and you understand the data impact.
4. Re-run smoke tests.

Log incidents + mitigations in your runbook after any rollback.
