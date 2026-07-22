# FounderConsole — Railway Deployment Guide

The chosen hosting path: Railway builds the repo's `Dockerfile` (one container running Express :5000 → FastAPI :8001 + simulation worker), with Railway-managed Postgres and Redis attached. TLS, domains, and deploys-on-push are all handled by Railway. `railway.json` in the repo root configures the build and the `/health` healthcheck.

> The VPS/Docker-Compose kit (`DEPLOYMENT.md`, `docker-compose.yml`, `deploy/`) remains in the repo as a fallback — Railway ignores those files.

```
Internet ──> Railway edge (TLS) ──> app container :5000 (Express → FastAPI + worker)
                                        ├── Postgres  (Railway service, DATABASE_URL reference)
                                        └── Redis     (Railway service, REDIS_URL reference)
```

## 1. Prerequisites

- Repo pushed to GitHub with the new files: `Dockerfile`, `.dockerignore`, `railway.json`, `deploy/railway-variables.example`.
- Secrets exported from the Replit Secrets pane (Resend, Perplexity, Twilio, Slack webhook, PostHog).
- Your own OpenAI / Anthropic / Gemini / OpenRouter API keys — the Replit-managed ones will not work off-platform.
- A Railway account (railway.com — sign in with GitHub).
- Optional but recommended: connect the **Railway connector** in claude.ai (Settings → Connectors → search "Railway") so Claude can deploy, tail logs, and debug for you afterwards.

## 2. Create the project

1. Railway dashboard → **New Project** → **Deploy from GitHub repo** → pick the repo.
   Choose the **EU (Amsterdam)** region — best latency from the UK.
2. Railway detects the Dockerfile and starts a build. The **first build will fail to become healthy** — expected, since the database and variables don't exist yet. Carry on.
3. In the same project: **+ New** → **Database** → **Add PostgreSQL**.
4. **+ New** → **Database** → **Add Redis**.

## 3. Configure variables

1. Open the **app service → Variables → Raw Editor**.
2. Paste the contents of `deploy/railway-variables.example` and fill in the blanks.
   The `${{Postgres.DATABASE_URL}}` / `${{Redis.REDIS_URL}}` lines are Railway references — they resolve automatically. If Railway named your database service something other than `Postgres`/`Redis`, adjust the reference names to match.
3. Save — Railway triggers a redeploy automatically.

First boot: `CREATE_SCHEMA=true` + `RUN_MIGRATIONS=true` create all 116 tables on an empty database. Watch it in **Deployments → View Logs**: you should see `[fastapi] Starting uvicorn`, schema creation, `FastAPI backend is ready`, then the worker starting. The deploy goes green once `/health` responds.

After the first healthy deploy, set `CREATE_SCHEMA=false` and `RUN_MIGRATIONS=false` in Variables.

## 4. Networking + domain

1. App service → **Settings → Networking → Generate Domain**, and when asked for the port enter **5000**. You get `something.up.railway.app` — use this to test everything before touching the real domain.
2. When ready to cut over: **Custom Domain** → enter `founderconsole.ai`. Railway shows you the DNS records to add (CNAME, or A/ALIAS records for an apex domain, depending on your DNS provider). Add `www` too if you use it.
3. Update `APP_BASE_URL` and `CORS_ORIGINS` variables to `https://founderconsole.ai` if you were testing with the railway.app URL.
4. TLS certificates are issued automatically once DNS propagates.

## 5. Smoke tests (on the railway.app URL first, then the real domain)

- `/health` returns OK
- Sign up → welcome email arrives (Resend)
- `/survival-simulator` runs and the share card renders
- `/simulate` Flight Simulator works (needs your OpenAI key)
- `/admin/growth` loads (needs `ADMIN_MASTER_EMAIL` to match your login)
- One data-connector sync
- Google OAuth login — update the authorized redirect URIs in Google Cloud Console if the domain changed (same domain = no change needed)

Then decommission the Replit deployment.

## 6. Day-to-day workflow

```bash
# on your Mac
npm run dev     # local dev as usual
git push        # → Railway builds and deploys automatically
```

Every push to the default branch deploys. Failed healthchecks keep the previous deployment live, and **Deployments → ⋮ → Rollback** restores any earlier build instantly.

With the Railway connector on in claude.ai, you can also just ask Claude to check deploy status, tail logs, or investigate an error — no dashboard needed.

## 7. Operations notes

- **Scaling** — Railway autoscales vertically up to your plan's limits per service; no instance sizes to pick. If Monte Carlo runs feel slow, check the service's CPU/memory graphs in Metrics.
- **Cost** — usage-based (~$10/GB RAM + ~$20/vCPU per month, prorated by actual usage) plus the Postgres/Redis services. Expect roughly $30–60/mo for this stack; the Usage page shows a live estimate. Set a **usage limit** in workspace settings to cap surprises.
- **Backups** — Railway Postgres supports backups on paid plans (service → Backups tab); enable a daily schedule. For an extra off-platform copy you can run `pg_dump` against the database's public connection URL from your Mac.
- **Logs** — Deployments → View Logs shows all three processes (Express, `[fastapi:out]`, `[worker:out]`) in one stream.
- **Redis** — optional by design; if it's ever down the app falls back to inline jobs.
- **Env changes** — editing Variables triggers a redeploy automatically (that's how the container picks them up).

## 8. Troubleshooting

- **Build succeeds, deploy never goes healthy** — check logs for missing `SECRET_KEY` or a `DATABASE_URL` reference that didn't resolve (service name mismatch). The healthcheck allows 10 minutes for first-boot schema creation.
- **502 on the public URL** — the domain's target port isn't 5000; fix in Settings → Networking.
- **AI features failing** — confirm your own `OPENAI_API_KEY` etc. are set in Variables (not the old Replit-managed ones).
- **Emails not sending** — Resend domain verification is account-level and carries over; check `RESEND_API_KEY`.
