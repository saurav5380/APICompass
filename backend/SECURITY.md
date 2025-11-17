# Security, privacy, and data handling

API Compass keeps a narrow data footprint and clear retention rules:

- **What we store:** Org metadata, encrypted provider credentials (AES-256), usage events and costs, alert rules/events, and audit logs for sensitive actions (connection changes, budget updates, alerts sent).
- **Retention:** Raw usage events are purged after `RAW_EVENT_RETENTION_DAYS` (default 180). Derived aggregates and audit logs remain for historical reporting unless you request deletion.
- **Subprocessors:** Postgres (database), Redis (queues/results), Stripe (billing), SendGrid/SES (notifications), Sentry (errors/telemetry if enabled).
- **Control:** `GET /api/data/export` provides a CSV export. `POST /api/data/delete` schedules an async purge of org-scoped data. Audit trails record who triggered key changes.
- **Transport & secrets:** TLS terminates at the edge; secrets stay in environment variables; provider credentials are encrypted at rest.

Contact security@api-compass.local for vulnerability disclosures or data rights requests.
