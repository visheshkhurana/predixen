# The deploy path — how FounderConsole gets to production without the Replit UI

Backlog item 7 asked for a deploy path that does not need the Replit UI. **That path already
exists and is already carrying traffic.** Production is Railway building the repo's `Dockerfile`
from `main` on every push. Nothing needs to be proposed except one missing piece: a way to read
the live commit sha off a running deployment (`/api/version`, section 3).

This document is the operational answer: what triggers a build, how to roll back, how to tell
which commit is live, and what the nightly database backup actually covers. It is written against
`main` at `9f492efebac05e230ee8af7801742d822e897e8e` and verified against live production on
2026-10-13 21:01 UTC.

`RAILWAY_DEPLOYMENT.md` remains the first-time setup guide (creating the project, adding Postgres
and Redis, pasting variables, cutting the domain over). This file is the day-to-day and
incident-time reference for the path that is now running.

## 0. What is actually serving production

Measured, read-only:

```
$ curl -sS -D - -o /dev/null https://founderconsole.ai/health
HTTP/2 200
server: railway-hikari
content-type: application/json; charset=utf-8
date: Tue, 13 Oct 2026 21:01:09 GMT
strict-transport-security: max-age=63072000; includeSubDomains; preload

$ curl -sS https://founderconsole.ai/api/health
{"status":"healthy","version":"1.0.0","environment":"production",
 "uptime_seconds":102397.5,"timestamp":"2026-10-13T21:01:09.595165+00:00",
 "ready":true,"routers_loaded":true,"database":"connected","redis":"connected",
 "startup_error":null}
```

`server: railway-hikari` is Railway's edge. The Replit deployment is not merely unused, it is
gone:

```
$ curl -sS -o /dev/null -w '%{http_code}\n' https://predixen-intelligence-os.replit.app/api/health
404
$ curl -sS https://predixen-intelligence-os.replit.app/api/health | grep -o "This app isn&#39;t live yet" | head -1
This app isn&#39;t live yet
```

So `.replit`, `REPLIT_DEPLOYMENT_GUIDE.md` and the `deploymentTarget = "gce"` declaration in
`.replit` are dead weight. They are harmless (Railway ignores them) and removing them is a
separate cleanup, not part of this item.

## 1. What triggers a build

**A push to the default branch (`main`) is the trigger.** That is the whole deploy process:
merging to `main` *is* deploying to production.

`railway.json` in the repo root is the contract:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 600,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5,
    "numReplicas": 1
  }
}
```

The `Dockerfile` builds one image that runs all three processes:

- stage `build` — `node:20-bookworm-slim`, `npm ci`, `npm run build` (Vite client + esbuild
  bundle to `dist/index.cjs`).
- stage `node-deps` — `npm ci --omit=dev`.
- stage `runtime` — `node:20-bookworm-slim` plus `python3`, `python3-venv`, `poppler-utils`,
  `curl`, `ca-certificates`; `uv` copied from `ghcr.io/astral-sh/uv:latest`; `uv sync --frozen
  --no-dev --no-install-project` into `/app/.venv`. It copies `node_modules`, `dist`,
  `package.json`, `server`, `shared`, `migrations`, `data`, `scripts`.
  `CMD ["node", "dist/index.cjs"]`, `EXPOSE 5000`.

Express on port 5000 spawns uvicorn on 8001 and the simulation worker, so one container runs all
three — the same process model Replit used. That is why the move to Railway needed no code change.

The measured commit-to-live gap is about eighteen seconds:

```
main's HEAD commit:              2026-10-12 16:33:09 UTC   (9f492efe, "Show simulation inputs on /simulate (#66)")
production's built asset:        2026-10-12 16:33:27 UTC   (/assets/index-2WfLLGEl.js, Last-Modified)
```

Other things that trigger a rebuild, all of which are deploys you should expect:

- **Changing any variable** on the app service. Railway redeploys automatically; this is how new
  values reach the container.
- **A manual redeploy** from the Railway dashboard (**Deployments → ⋮ → Redeploy**).
- A change to `railway.json` or the `Dockerfile` (they are in the image path, so they rebuild).

**What is not a deploy trigger:** CI. `.github/workflows/pr-checks.yml` runs on every pull
request, on every push to `main`, and on demand (PR #125; PR #52 merged the first version,
2026-10-13T22:19:32Z). This paragraph used to say `pull_request` targeting `main`, and that
was wrong twice over: the clause carried a `branches:` filter, and under `pull_request`
`branches` filters on the **base** branch, so every stacked PR was skipped silently while
GitHub still reported it clean - "clean" means "no conflict", never "tested". The filter is
gone, so a PR stacked on another PR's branch is checked like any other. The `on:
workflow_dispatch: {}` line this paragraph used to quote, and its claim that paid Actions
minutes were never approved, were both wrong - the repository is public, so standard
`ubuntu-latest` runners cost nothing and there was never a spend decision. **A direct push to
`main` is now checked, but still unguarded:** the `push:` trigger to `main` means committing
straight to `main` starts a run - so the head is checked, but that run gates nothing.
Railway's build is not gated on any check passing, so **nothing stops a red
direct push from reaching production.** Nothing gates a branch against live traffic but a
human reading the pull request - the check is a signal, not a gate.

## 2. How to roll back

Railway keeps every previous deployment, so a rollback does not need a code change.

**Fastest — revert in git (preferred).** It keeps `main` and production in agreement, which is
what makes the merge gate's condition (`main` matches production) stay true:

```
git revert <bad-sha>          # or: git revert -m 1 <merge-sha>
git push origin main          # god/Michael owns this push
```

Railway builds the revert and the previous behaviour is live again in about a minute.

**Dashboard rollback (when you need it in seconds, and accept the drift).**
Railway → the app service → **Deployments** → find the last good deployment → **⋮ → Rollback**.
The old image is restored immediately without rebuilding. The cost is that `main` now says
something production is not running, so *do the git revert as well* or the next push
silently un-rolls you.

**What a failed deploy does on its own.** `railway.json` sets `healthcheckPath: /health` with
`healthcheckTimeout: 600` and `restartPolicyType: ON_FAILURE` / `restartPolicyMaxRetries: 5`.
A build that never becomes healthy does not replace the running deployment — Railway keeps the
previous one live. So a bad push degrades to "the fix did not ship", not "the site is down",
*provided* the image still starts. A commit that breaks the build outright fails at build stage
and likewise leaves the last good deployment serving.

**Do not roll back by force-pushing `main`.** Rewriting shared history is on the
`OPERATING-MODEL.md` "always goes to Vishesh first" list, and it breaks every other agent's clone
and any open pull request.

**What has no rollback:** a database migration that already ran. `CREATE_SCHEMA` and
`RUN_MIGRATIONS` are set `true` for first boot and should be `false` after. Rolling the image back
does not roll the schema back. That is why a production migration needs a same-day
`scripts/db_backup.py` backup before it is applied.

## 3. How to tell which commit is live

**Today you cannot read it off production.** There is no build stamp. Measured:

```
$ curl -sS -o /dev/null -w 'HTTP %{http_code}\n' https://founderconsole.ai/api/version
HTTP 404
```

The `"version":"1.0.0"` in `/api/health` is not a commit — it is a hard-coded constant that has
never been bumped per release:

```python
# server/main.py:29
APP_VERSION = "1.0.0"
```

`server/main.py:495` returns it in the health payload, and Express `/health` proxies FastAPI's
`/health` (`server/index.ts:90`), which is why the same JSON appears on both paths.

**The indirect workaround, for right now.** Two signals, used together:

```
# 1. when the running front end was built
curl -sS -I https://founderconsole.ai/assets/index-<hash>.js | grep -i last-modified

# 2. the newest commit before that timestamp
git log -1 --format='%H %ci %s' --before='<that timestamp>' origin/main
```

That is how backlog item 1 concluded production was running `9f492efe` — an eighteen-second gap
between the commit and the built asset. It is inference from a timestamp, not a read of the
running commit, and it silently drifts if Railway ever serves a cached asset.

### Proposal — add the sha to `/api/health`

One field, one line of Python, and this becomes a single command. In `server/main.py`, inside the
`health()` return dict (after `"version": APP_VERSION,`):

```python
        "version": APP_VERSION,
        "commit": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "unknown"),
```

`RAILWAY_GIT_COMMIT_SHA` is Railway's own variable for services deployed from a GitHub repo, and
**nothing in the repo reads it today** — verified:

```
$ grep -rn "RAILWAY_GIT_COMMIT_SHA\|RAILWAY_ENVIRONMENT" . --exclude-dir=.git
(no matches)
```

The `"unknown"` fallback matters: local dev and any non-Railway host keep working, and the field
is present either way so a caller can tell "not deployed by Railway" from "deployed, sha missing".

**This has not been verified against a live Railway deploy**, because I have no Railway access
from this machine. The confirmation step is one command on the first deploy after the patch lands:

```
curl -sS https://founderconsole.ai/api/health | python3 -c 'import json,sys; print(json.load(sys.stdin)["commit"])'
```

If that prints `unknown` on a Railway deploy, the variable is not being injected and the fallback
is to bake the sha at build time instead (write it to a file in the image and read that).
Either way `/api/version` is the right shape for the check, and it also gives
`scripts/launch_gate.sh` something to assert against.

This is a code change, so it is **not** part of this docs PR. It is worth its own backlog item.

## 4. What `railway-db-backup.yml` covers

`.github/workflows/railway-db-backup.yml` is the only automated database backup in the repo.

- **Trigger:** `schedule: cron "0 7 * * *"` — daily at 07:00 UTC — plus manual
  `workflow_dispatch`. Concurrency group `db-backup` with `cancel-in-progress: false`, so a
  manual run never truncates a scheduled one.
- **Job:** `dump`, `runs-on: ubuntu-latest`, `timeout-minutes: 15`.
- **Client:** installs `postgresql-client-18` explicitly, because the runner's stock `pg_dump`
  is version 16 and refuses to dump an 18.x server.
- **The dump:** `pg_dump "$DATABASE_URL" -Fc -f "founderconsole_${STAMP}.dump"` — the custom
  format, so it restores with `pg_restore`.
- **Guard:** the workflow reads `RAILWAY_DATABASE_URL` and **errors out if it is unset**. So a
  missing secret fails loudly instead of writing an empty file.
- **Retention:** the dump is always uploaded as the artifact `db-backup-${{ github.run_id }}`
  with `retention-days: 30` and `if-no-files-found: error`. Thirty days of daily dumps.
- **Off-platform copy:** only if `secrets.BACKUP_S3_BUCKET` is set does it also push to S3 or
  Backblaze B2, using `BACKUP_S3_KEY`, `BACKUP_S3_SECRET` and `BACKUP_S3_ENDPOINT`.

What it **does not** cover:

- **Restore is not tested.** There is no workflow that restores a dump, so retention is proven
  and recoverability is not.
- **The `pg_dump` runs against whatever `RAILWAY_DATABASE_URL` points at**, which for a
  Railway-managed Postgres is the public connection URL — the traffic path is not the same one
  the app uses internally.
- **The workflow's "do not wire a backup secret" sibling.** `pr-checks.yml` carries an explicit
  instruction not to wire `RAILWAY_DATABASE_URL` into it. The two files are deliberately
  separate; do not merge them.

**Unverified, and it matters:** I could not confirm whether this workflow has ever run. `gh` is
installed and the repo is configured, but every GitHub API call from this machine fails on TLS
through the sandbox's filtering proxy:

```
$ gh run list --workflow=railway-db-backup.yml --limit 10
failed to get runs: Get "https://api.github.com/repos/visheshkhurana/predixen/actions/workflows/railway-db-backup.yml": tls: failed to verify certificate: x509: OSStatus -26276
```

Two consequences, both worth a card:

1. **Withdrawn 2026-10-14 - both halves of this were false.** The repository is **public**
   (`visibility: public`, measured 2026-10-14), so a scheduled workflow on `runs-on:
   ubuntu-latest` consumes nothing: there is no unapproved spend and no HAG-154 blocker here.
   And the backup is not dead - `GET /actions/workflows/railway-db-backup.yml/runs` ->
   `total_count 84`, newest `38415935614 schedule 2026-10-13T14:44:15Z success`. **The only
   part worth keeping is the last clause:** a backup that stops running produces no failure,
   so it wants a monitor, not a spend decision.
2. Railway Postgres has its own backups tab, but `RAILWAY_DEPLOYMENT.md` describes it as a paid
   feature ("Railway Postgres supports backups on paid plans"). If the plan does not include it,
   this GitHub workflow is the only copy, and it needs to be confirmed running.

## 5. Deploy checklist

Before pushing to `main`:

1. `npm run check`, `pytest server/tests`, `python qa-lab/runner/qa_runner.py` locally. (Never
   `qa-lab/run.sh` — it also pushes the report to Notion.) Do **not** run `scripts/launch_gate.sh`
   against a branch: it hits live production.
2. Nothing in the diff is a production migration, or a same-day `scripts/db_backup.py` backup
   exists.
3. Nobody is mid-incident: check Railway → Deployments for a rollback in the last few minutes.
4. `RESEND_WEBHOOK_SECRET` is set in Railway. Both Resend receivers fail **closed**: with the
   secret unset they return `503` and drop real delivery events rather than record them
   unverified. Set it **before** the push, not after.

After the push:

1. Watch **Deployments → View Logs**. Expect `[fastapi] Starting uvicorn`, then
   `FastAPI backend is ready`, then the worker starting. All three processes log to one stream
   (`[fastapi:out]`, `[worker:out]`).
2. The deploy goes green when `/health` answers. With the healthcheck at 600 s, a bad deploy is
   slow to declare itself — the old deployment keeps serving meanwhile.
3. `curl -sS https://founderconsole.ai/api/health` and check `status`, `database`, `redis`.
4. Once the `/api/version` proposal lands, assert the sha matches the commit you pushed.

## 6. What this document does not fix

- **No CI gate between a branch and production** (item 4 / HAG-154). Railway deploys any push to
  `main`, green or not.
- **No build stamp** — the `/api/version` patch above is proposed, not applied.
- **The nightly backup's liveness is unconfirmed** (section 4).
- **`.replit` and the Replit docs are stale** but harmless; deleting them is its own small PR.

## 7. Boundaries

Read-only against production: no writes, no deploys, no config changes, no Railway access, no
secrets read. The only state change was on this machine, in a scratch clone under `$TMPDIR`, to
produce this document.

Co-Authored-By: Claude Code <noreply@anthropic.com>
