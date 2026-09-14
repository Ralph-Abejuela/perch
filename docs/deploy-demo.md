# Deploying the Perch demo

Topology (ADR 0002): **Cloudflare Pages** hosts the dashboard + demo landing, a **VPS** runs the backend in Docker, and a **Cloudflare Tunnel** connects them — no open inbound ports, free TLS.

```text
browser ─ pages.dev (dashboard, demo page)
              │  fetch/WebSocket → https://api.your-domain.com
              ▼
        Cloudflare edge ── Tunnel ── VPS: docker compose (app + db + redis + cloudflared)
```

## 1. Backend on the VPS

```sh
# on the VPS (Ubuntu, Docker + compose plugin installed)
git clone https://github.com/ralph-abejuela/perch.git && cd perch
cp .env.example .env
# edit .env: set PERCH_JWT_SECRET to a long random string
```

Create the tunnel (once, from any machine with cloudflared or via the Zero Trust dashboard):

```sh
cloudflared tunnel login
cloudflared tunnel create perch
cloudflared tunnel route dns perch api.your-domain.com
```

Put the tunnel token in `.env` (`CLOUDFLARE_TUNNEL_TOKEN=...`) and bring everything up:

```sh
docker compose -f docker-compose.yml -f compose.cloudflared.yml up -d
```

Verify: `curl https://api.your-domain.com/health` → `{"status":"ok"}`.

## 2. Dashboard + demo on Cloudflare Pages

1. Cloudflare dashboard → Workers & Pages → create two **Pages** projects:
   - `perch-dashboard`
   - `perch-demo`
2. In the GitHub repo settings → Secrets → Actions, add:
   - `CLOUDFLARE_API_TOKEN` (Pages: Edit permission)
   - `CLOUDFLARE_ACCOUNT_ID`
3. Push to `main` (or run the "Deploy demo" workflow manually). It deploys:
   - `frontend/dist` → perch-dashboard
   - `widget/demo` → perch-demo

## 3. Wire it together

1. Sign up on the dashboard, create a Site, copy its key.
2. Set the API origin the dashboard talks to (same-origin reverse proxy on Pages, or `PERCH_CORS_ORIGINS=https://<dashboard>.pages.dev` on the backend with `PERCH_COOKIE_SAMESITE=none` + `PERCH_COOKIE_SECURE=true` since it's TLS).
3. Open the demo page with your key:

```text
https://<perch-demo>.pages.dev/?site=YOUR_SITE_KEY&api=https://api.your-domain.com
```

4. Chat from the demo page; answer from the dashboard inbox.

## Updating

Push to `main` → CI runs tests → the demo workflow redeploys Pages. Backend updates: `git pull && docker compose ... up -d --build`, or tag `vX.Y.Z` to publish a new image to Docker Hub and `docker compose pull && up -d`.
