# Perch

Self-hostable live chat widget. A business (Tenant) embeds a widget on their website; their Agents answer Visitor conversations in real time from a dashboard.

- Multi-tenant (shared database, `tenant_id` rows)
- Realtime over WebSockets (fanout via Redis pub/sub, presence, typing)
- FastAPI + PostgreSQL + Redis
- React + Vite + TypeScript dashboard, tiny embeddable widget bundle
- One Docker image, self-hostable via `docker compose up`
- AGPL-3.0

## Status

v1 in development. See [CONTEXT.md](./CONTEXT.md) for the domain glossary and [docs/adr/](./docs/adr/) for architecture decisions.

## Quick start (development)

```sh
docker compose up --build
```

- Backend API: http://localhost:8000 (docs at `/docs`)
- Dashboard: see `frontend/`
- Widget: see `widget/`

## Self-hosting

```sh
docker compose up -d
```

Services: `app` (FastAPI), `db` (Postgres 16), `redis` (Redis 7), and an optional `cloudflared` service for exposing the backend through a Cloudflare Tunnel (see `docker-compose.yml`).

## Layout

```
backend/    FastAPI app
frontend/   Agent dashboard (React + Vite + TS)
widget/     Embeddable chat widget (TS, IIFE bundle)
docs/adr/   Architecture decision records
```

## License

AGPL-3.0 — see [LICENSE](./LICENSE).
