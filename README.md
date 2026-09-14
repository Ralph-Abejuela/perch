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
cp .env.example .env        # set PERCH_JWT_SECRET!
docker compose up -d
```

Services: `app` (FastAPI, port 8000), `db` (Postgres 16), `redis` (Redis 7), and an optional `cloudflared` service for exposing the backend through a Cloudflare Tunnel (see `docker-compose.yml`).

Then:

1. Open `http://localhost:8000/docs` to verify, and deploy the dashboard (`frontend/dist`) to any static host pointing at your API origin.
2. Sign up, create a Site, and embed the widget:

```html
<script src="https://your-api-origin/widget.js" data-site-key="YOUR_SITE_KEY" data-api="https://your-api-origin"></script>
```

The API serves the widget bundle itself at `/widget.js` — no separate hosting needed.

If the dashboard is hosted on a different domain, set `PERCH_CORS_ORIGINS`, `PERCH_COOKIE_SAMESITE=none`, and `PERCH_COOKIE_SECURE=true` (TLS required).

## Releases

GitHub Actions runs pytest on every push and publishes the Docker image to Docker Hub on `v*` tags (requires `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` repo secrets).

## Layout

```
backend/    FastAPI app
frontend/   Agent dashboard (React + Vite + TS)
widget/     Embeddable chat widget (TS, IIFE bundle)
docs/adr/   Architecture decision records
```

## License

AGPL-3.0 — see [LICENSE](./LICENSE).
