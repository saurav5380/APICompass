# Prisma Schema (Future B2B Features)

## Current Status: NOT IN USE

This Prisma schema is **prepared but not implemented** in the frontend.

### Why It Exists

- **Future B2B features**: Multi-user dashboards, admin panels, team management
- **Performance**: Direct database reads for server-side rendering
- **Scalability**: Reduce FastAPI load by bypassing API for simple reads

### Current Architecture

```
Frontend (Next.js) → fetch() → FastAPI → SQLAlchemy → PostgreSQL
```

### Future Architecture (B2B)

```
Frontend Server Components → Prisma → PostgreSQL (reads)
Frontend Client Components → fetch() → FastAPI → PostgreSQL (writes)
```

### Important Notes

1. **Schema Sync**: This schema mirrors `backend/api_compass/models/tables.py`
2. **Source of Truth**: SQLAlchemy is the primary schema definition
3. **Manual Sync Required**: When backend models change, update this schema
4. **Migrations**: Alembic handles migrations, Prisma just reads the schema

### When to Implement

- Adding multi-user features (teams, user management)
- Building B2B admin dashboards
- Optimizing page load performance for server-side rendering
- Scaling to handle more concurrent users

### Implementation Checklist

- [ ] Create `src/lib/prisma.ts` client wrapper
- [ ] Sync Prisma migration state with Alembic history
- [ ] Convert pages to Next.js Server Components
- [ ] Add environment variable `DATABASE_URL` to frontend
- [ ] Test RLS policies work with Prisma queries
- [ ] Document read/write separation pattern

## Reference

- Backend Models: `backend/api_compass/models/tables.py`
- Alembic Migrations: `backend/alembic/versions/`
- Prisma Docs: https://www.prisma.io/docs
