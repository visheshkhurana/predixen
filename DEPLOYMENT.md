# FounderConsole — VPS Deployment Guide

Self-hosting the platform off Replit with Docker Compose. One app container runs all three processes (Express gateway on :5000, which itself spawns FastAPI on :8001 and the simulation worker), plus Postgres 16, Redis 7, and Caddy for automatic HTTPS.

```
Internet ──443──> Caddy (auto-TLS) ──> Express :5000 ──> FastAPI :8001
                                          │                  │
                                          └── serves SPA     ├── Postgres 16 (volume: pgdata)
                                                             └── Redis 7    (volume: redisdata)
```

## 0. Choosing a VPS

The stack wants ~4 vCPU / 8 GB RAM (numpy/scipy Monte Carlo runs, ThreadPoolExecutor workers, Postgres, plus Vite builds on-box).

| Provider | Plan | Specs | ~Price/mo |
|---|---|---|---|
| **Hetzner (recommended)** | CPX31 | 4 vCPU AMD, 8 GB, 160 GB NVMe | ~€16–17 |
| Hetzner (budget) | CX32 | 4 vCPU Intel shared, 8 GB, 80 GB | ~€7–8 |
| DigitalOcean | Basic 8 GB | 4 vCPU, 8 GB, 160 GB | ~$48 |
| OVH | VPS Comfort | 4 vCPU, 8 GB | ~£12 |

Hetzner gives by far the best price/performance; pick a Falkenstein or Nuremberg location (fine latency from the UK). Choose **Ubuntu 24.04 LTS** as the OS and add your SSH key when creating the server. You can start on the CX32 and resize up later if sims feel slow — Hetzner resizes in place.

Note: prices move — check current pricing when you order.

## 1. One-time server setup

SSH in as root, then:

```bash
# copy the bootstrap script up (from your laptop, in the repo root)
scp deploy/setup-vps.sh root@YOUR_SERVER_IP:/root/

# on the server
bash /root/setup-vps.sh
```

This installs Docker, enables a firewall (SSH/80/443 only), fail2ban, automatic security updates, a 2 GB swapfile, and creates an `app` user with Docker access.

## 2. Get the code onto the server

```bash
su - app
git clone https://github.com/visheshkhurana/predixen.git founderconsole
cd founderconsole
```

(Push your latest from Replit to GitHub first if you haven't.)

## 3. Configure secrets

```bash
cp deploy/env.production.example .env.production
nano .env.production
```

Fill in everything — the file documents each value and how to generate the random ones. Two important notes:

- **Export your secrets from the Replit Secrets pane** before you shut anything down there (RESEND_API_KEY, PERPLEXITY_API_KEY, Twilio, Slack webhook, PostHog).
- **AI keys:** the OpenAI/Anthropic/Gemini/OpenRouter credentials Replit injected will NOT work off-platform. Create your own keys on each provider's dashboard.

For the first boot leave `CREATE_SCHEMA=true` and `RUN_MIGRATIONS=true` (fresh database gets its 116 tables created at startup). After the first successful boot, set both to `false`.

## 4. First deploy

```bash
bash deploy/deploy.sh --no-pull
```

First build takes several minutes (npm ci + Vite build + Python deps). The script waits until the app reports healthy. Watch logs with:

```bash
docker compose logs -f app
```

You should see `[fastapi] Starting uvicorn`, then schema creation, then `FastAPI backend is ready` and the worker starting.

## 5. DNS + HTTPS

At your DNS provider, point the domain at the server:

| Type | Name | Value |
|---|---|---|
| A | @ | YOUR_SERVER_IP |
| A (or CNAME) | www | YOUR_SERVER_IP (or @) |

Lower the TTL to 300s ahead of time if the domain is currently live on Replit, so cutover is quick. Once DNS resolves to the server, Caddy fetches Let's Encrypt certificates automatically — no certbot, no renewal cron. Check with:

```bash
curl -I https://founderconsole.ai/health
```

Until you're ready to move the real domain, you can test with any spare domain/subdomain — just set `DOMAIN=` in `.env.production` accordingly.

## 6. Post-cutover checklist

1. **Google OAuth** — add `https://founderconsole.ai` redirect URIs pointing at the new host in Google Cloud Console (only needed if the domain changed; same domain = no change).
2. **Smoke tests** (from the handover doc):
   - Sign up → welcome email arrives (Resend)
   - `/survival-simulator` runs and the share card renders
   - `/simulate` Flight Simulator works (needs your OpenAI key)
   - `/admin/growth` loads (needs `ADMIN_MASTER_EMAIL` to match your login)
   - One data-connector sync
3. **Backups** — install the nightly cron:
   ```bash
   crontab -e
   # add:
   15 2 * * * cd /home/app/founderconsole && bash deploy/backup-db.sh >> backups/backup.log 2>&1
   ```
   Also consider Hetzner's server-level backup option (~20% of server price) as a second layer.
4. Set `CREATE_SCHEMA=false` and `RUN_MIGRATIONS=false` in `.env.production`, then `docker compose --env-file .env.production up -d`.
5. Decommission the Replit deployment once you're happy.

## 7. Day-to-day: shipping improvements

Your new workflow for features and fixes:

```bash
# on your Mac: develop as usual
npm run dev            # local dev (Express :5000 + FastAPI :8001)
git push               # push to GitHub

# on the VPS: ship it
ssh app@YOUR_SERVER_IP
cd founderconsole && bash deploy/deploy.sh
```

`deploy.sh` pulls, rebuilds the image, restarts containers, and verifies health. There's ~10–30s of downtime during the swap — fine at current scale; a zero-downtime setup (second app container + Caddy load-balancing) is an easy later upgrade.

Useful operations:

```bash
docker compose logs -f app          # live logs, all three processes
docker compose logs -f caddy        # TLS / request logs
docker compose restart app          # restart app only
docker compose exec db psql -U fundflow fundflow    # SQL console
docker compose exec app /app/.venv/bin/python -m pytest server/tests  # if/when tests are wired
bash deploy/backup-db.sh            # manual backup
```

## 8. Troubleshooting

- **App unhealthy / restart loop** — `docker compose logs --tail=200 app`. Most common causes: missing `SECRET_KEY`/`POSTGRES_PASSWORD`, or first boot with `CREATE_SCHEMA=false` on an empty DB.
- **No HTTPS certificate** — DNS not pointing at the server yet, or port 80/443 blocked. `docker compose logs caddy` shows the ACME attempts.
- **AI features failing** — keys were Replit-managed; confirm your own `OPENAI_API_KEY` etc. are set and the container was restarted after editing `.env.production` (`docker compose --env-file .env.production up -d` re-reads it).
- **Emails not sending** — Resend domain verification is account-level, so it carries over; check `RESEND_API_KEY` is the same one.
- **Out of memory during build** — the swapfile usually covers it; otherwise build on your Mac and `docker save`/`scp`/`docker load`, or resize the server temporarily.
- **Redis** — optional by design; if the redis container is down the app falls back to inline jobs. Check `docker compose ps`.

## 9. What was intentionally left out

- **Data migration** — you chose a fresh database. If you change your mind, `pg_dump` the Replit DB and pipe it into the db container before first signup (restore command is at the bottom of `deploy/backup-db.sh`).
- **Stripe** — paywall stays paused; wire `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` and re-enable `PaywallMiddleware` when ready.
- **CI/CD** — deploys are a one-line SSH command for now. A GitHub Action that SSHes and runs `deploy.sh` on push to `main` is a natural next step.
