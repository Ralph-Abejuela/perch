# Demo deploys on a VPS behind a Cloudflare Tunnel

Cloudflare Pages/Workers cannot run the Python backend, so the public demo runs as: dashboard + widget bundle on Cloudflare Pages, backend on a cheap VPS in Docker, reached from the edge via a Cloudflare Tunnel (zero open inbound ports, free TLS). The demo URL and a self-hoster's setup are the same topology, so the demo doubles as proof of the self-host story.

Considered and rejected:

- **Cloudflare Python Workers** — beta, no real Redis, no Docker story; undercuts the Docker Hub goal.
- **Proxied DNS + Nginx on the VPS** — simpler mental model but exposes the origin IP and adds cert management.
- **Fly.io/Render free tier** — zero ops but split-brain story and shaky free-tier reliability.

Consequences: `cloudflared` is a required container in the demo's compose file; the VPS needs no public ports except outbound.
