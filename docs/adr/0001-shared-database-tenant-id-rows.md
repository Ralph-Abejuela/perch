# Multi-tenancy via shared database, tenant_id rows

Perch must serve many Tenants from one self-hostable deployment (one Docker image + Postgres + Redis). We chose a single shared Postgres schema where every tenant-owned table carries a `tenant_id` column, scoped in the application layer. This is the standard SaaS pattern (Slack-style), the simplest to migrate and back up, and adequate isolation for the threat model (Tenants trust the operator of their own deployment).

Considered and rejected:

- **Postgres RLS on top of tenant_id rows** — stronger guarantee, worth adding later as hardening; not needed for v1.
- **Schema-per-tenant** — real isolation but migrations must fan out across N schemas; overkill at this scale.

Consequences: every query path must be tenant-scoped in one place (repository/dependency layer), never per-handler; a missed scope is a data leak, so scope checks live in a single shared mechanism.
