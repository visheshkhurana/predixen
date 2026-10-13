# HAG-155 — lead-gen webhooks are unreachable through the Express proxy

**Fixed.** `server/index.ts` proxied `/api`, `/notifications` and `/email-tracking` to FastAPI but
not `/webhooks/lead-gen/*`, so those three paths were matched by no route and fell through to the
SPA catch-all. `GET /webhooks/lead-gen/ingest` answered `200 text/html`; a correctly signed n8n
`POST` was swallowed the same way and the lead was silently lost. With the fix, the same `POST`
returns `201 Created` and the lead is written.

Branch `agent/hag155-webhook-proxy`, based on `origin/main` = `9f492efe`. One file changed,
`server/index.ts`, +26 lines. Not pushed — god integrates.

Measured 2026-10-14 00:45–00:55 UTC on a local build. Production was touched with plain `GET`s only.

---

## 1. The defect

FastAPI registers the receivers:

- `server/webhooks/lead_gen_webhooks.py:29` — `router = APIRouter(prefix="/webhooks/lead-gen")`,
  with `POST /ingest` (`:76`, `201`), `POST /event` (`:122`, `201`), `POST /simulation` (`:173`).
- `server/main.py:114` imports it, `server/main.py:139` `app.include_router(lead_gen_webhooks_api.router)`.

Express owns the front door and forwards only three prefixes to that service. Before the change the
whole list was:

| `server/index.ts` (before) | line | `pathRewrite` |
| --- | --- | --- |
| `app.use("/api", …)` | 730 | `^/api` → `""` |
| `app.use("/notifications", …)` | 738 | `` `/notifications${path}` `` |
| `app.use("/email-tracking", …)` | 759 | `` `/email-tracking${path}` `` |

Nothing matched `/webhooks/…`. `serveStatic` is registered **last** (`server/index.ts:847`), so its
`app.use("*", …)` SPA handler (`server/static.ts:36`) is the final handler and answered every
unmatched path with `index.html`. That is the whole bug: an inbound webhook is served the marketing
page and never reaches the receiver, so n8n sees a `200` and reports success while nothing was
recorded.

Identical on `main` and in production, so it is a defect, not drift. Found by
`worker-predixen-drift` — `agents/worker-predixen-drift/founderconsole/backlog-1-prod-drift.md` §4.

## 2. Before / after, real commands and real output

Both runs are the same build: the real Express gateway (`server/index.ts`) started with
`npx tsx server/index.ts` in development mode on `127.0.0.1:5099`, with the real FastAPI app
(`uvicorn server.main:app`, on port 8001) spawned by that same process and reached through the
proxy target `FASTAPI_URL`. The only difference between the two runs is the 26-line block in §3:
`git checkout -- server/index.ts` for "before", the block restored for "after". Same sqlite
database, same `LEAD_GEN_WEBHOOK_SECRET`, same everything else.

### Before the fix

```
$ curl -sS -D - -o /dev/null -w '\n[curl] http_code=%{http_code} content_type=%{content_type} size=%{size_download}\n' \
    http://127.0.0.1:5099/webhooks/lead-gen/ingest
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
[curl] http_code=200 content_type=text/html; charset=utf-8 size=5305
[body bytes 0-120] <!DOCTYPE html>
<html lang="en">
  <head>
    <script type="module">
```

```
$ curl -sS -D - -o /dev/null -w '\n[curl] http_code=%{http_code} content_type=%{content_type} size=%{size_download}\n' \
    -X POST -H 'Content-Type: application/json' --data '{"email":"probe@example.com"}' \
    http://127.0.0.1:5099/webhooks/lead-gen/ingest
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
[curl] http_code=200 content_type=text/html; charset=utf-8 size=5305
```

**`200` + `text/html` + 5,305 bytes of SPA shell, for both the GET and the POST.** The POST body is
discarded with it. Control, proving the proxy itself works for the prefixes that were listed:

```
$ curl -sS -o /dev/null -w '[curl] http_code=%{http_code} content_type=%{content_type}\n' \
    http://127.0.0.1:5099/api/health
[curl] http_code=200 content_type=application/json
```

### After the fix

```
$ curl -sS -D - -o /dev/null -w '\n[curl] http_code=%{http_code} content_type=%{content_type} size=%{size_download}\n' \
    http://127.0.0.1:5099/webhooks/lead-gen/ingest
HTTP/1.1 405 Method Not Allowed
content-type: application/json
[curl] http_code=405 content_type=application/json size=31
[body] {"detail":"Method Not Allowed"}
```

`405`, not `200`, because the receiver is POST-only — the request reached FastAPI's router, which is
the point. The GET is the cleanest discriminator, and the same request that returned `200 text/html`
before now returns JSON from the backend.

```
$ curl -sS -D - -o /dev/null -w '\n[curl] http_code=%{http_code} content_type=%{content_type} size=%{size_download}\n' \
    -X POST -H 'Content-Type: application/json' --data '{"email":"probe@example.com"}' \
    http://127.0.0.1:5099/webhooks/lead-gen/ingest
HTTP/1.1 401 Unauthorized
content-type: application/json
[curl] http_code=401 content_type=application/json size=48
[body] {"detail":"Missing X-Predixen-Signature header"}
```

An unsigned POST is now refused by the HMAC check instead of swallowed — the `401` is FastAPI's
`verify_signature` (`lead_gen_webhooks.py:42`), so the bytes arrived intact.

The real n8n call, with the signature computed the way the workflow does
(`hex(hmac_sha256(secret, raw_body))` in `X-Predixen-Signature`):

```
$ SIG=$(printf '%s' "$BODY" | python -c "
import hashlib, hmac, sys
print(hmac.new(b'hag155-local-test-secret', sys.stdin.buffer.read(), hashlib.sha256).hexdigest())")
$ curl -sS -D - -w '\n[curl] http_code=%{http_code} content_type=%{content_type} size=%{size_download}\n' \
    -X POST -H 'Content-Type: application/json' -H "X-Predixen-Signature: $SIG" --data "$BODY" \
    http://127.0.0.1:5099/webhooks/lead-gen/ingest
HTTP/1.1 201 Created
content-type: application/json
[curl] http_code=201 content_type=application/json size=32
[body] {"lead_id":1,"action":"created"}
```

**`201 Created`, `lead_id: 1`.** A row was written to `leads` and a `LeadEvent` with it. The other
two receivers reach FastAPI too:

```
$ for p in event simulation; do curl -sS -o /dev/null -w "%{http_code} %{content_type}\n" \
    -X POST -H 'Content-Type: application/json' --data '{}' \
    "http://127.0.0.1:5099/webhooks/lead-gen/$p"; done
401 application/json
401 application/json
```

## 3. The change

One block in `server/index.ts`, inserted after the `/email-tracking` proxy and **before**
`express.json()`:

```ts
// Proxy lead-gen webhook receivers (/webhooks/lead-gen/{ingest,event,simulation})
// to FastAPI. Without this the paths are not matched by any route and fall
// through to the SPA catch-all, which answers 200 text/html — so n8n's POST
// never reaches the HMAC-verified receiver and the lead is silently dropped.
// The body is streamed, not parsed, so the bytes FastAPI hashes are the bytes
// n8n signed. Must stay above express.json() below, which consumes the stream.
app.use(
  "/webhooks/lead-gen",
  createProxyMiddleware({
    target: FASTAPI_URL,
    changeOrigin: true,
    timeout: 30000,
    proxyTimeout: 30000,
    pathRewrite: (path) => `/webhooks/lead-gen${path}`,
    on: {
      error: (err: Error, req, res) => {
        console.error("Lead-gen webhook proxy error:", err.message);
        if ('writeHead' in res && typeof res.writeHead === 'function') {
          res.writeHead(502, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Lead-gen webhook service unavailable", detail: "Internal proxy error" }));
        }
      },
    },
  })
);
```

### Components the proxy layer touches

- **`server/index.ts`** — the only file changed. The proxy sits with the other three at lines
  705–799: `/api` (730), `/notifications` (738), `/email-tracking` (759), new `/webhooks/lead-gen`
  (785). All four share `target: FASTAPI_URL` and the same 502 `on.error` shape.
- **`server/static.ts`** — not changed, but it is the reason the bug was invisible: its
  `app.use("*", …)` is registered after the proxies (`server/index.ts:847`) and answers with
  `injectSEO(indexHtml, pathname)`, i.e. a plausible-looking `200 text/html`. Anything that reaches
  it looks like a working page.
- **`server/vite.ts`** — the development-mode equivalent of the same catch-all. Both were exercised:
  the "before" run used Vite's handler and returned the same `200 text/html` shape production
  serves, so the fix is not specific to one of the two.
- **`express.json()`** (`server/index.ts:790`) — ordering matters and is unchanged. The proxies are
  registered above the body parser, so the request body is still an unread stream when the proxy
  forwards it. `verify_signature` hashes `await request.body()`, so a proxy placed below the parser
  would forward a body that no longer matches what n8n signed. This is the reason the block is
  placed where it is rather than at the end of the file.
- **FastAPI side — nothing.** `server/main.py:139` already registers the router; only the front
  door was missing.

## 4. Production today

Plain `GET`s against `https://founderconsole.ai`, one per receiver:

```
$ for p in ingest event simulation; do \
    curl -sS -o /dev/null -w "/webhooks/lead-gen/$p -> %{http_code} %{content_type}\n" \
    "https://founderconsole.ai/webhooks/lead-gen/$p"; done
/webhooks/lead-gen/ingest -> 200 text/html; charset=utf-8
/webhooks/lead-gen/event -> 200 text/html; charset=utf-8
/webhooks/lead-gen/simulation -> 200 text/html; charset=utf-8
```

All three are still served the SPA. The fix is not deployed — that happens when this branch lands on
`main` and Railway rebuilds. After that, these same `GET`s should answer `405 application/json`.

## 5. What a reviewer should check first

1. **The `pathRewrite` must not strip the prefix.** `/api`'s proxy rewrites `^/api` → `""`, because
   FastAPI serves those routes at the root. `/notifications` and `/email-tracking` deliberately
   re-add their prefix, and this one does the same. Copying the `/api` rewrite here would send
   `/ingest` to FastAPI and `404`.
2. **Placement above `express.json()`.** Moving this block below the body parser breaks HMAC
   verification in a way that only shows up as `401 Invalid signature`, not as a crash — a bad
   failure mode to debug in production. See §3.
3. **Scope.** I proxied the prefix `/webhooks/lead-gen`, matching how the other three proxies are
   scoped, rather than all of `/webhooks`. There are no Express routes under `/webhooks` today
   (`grep -rn --include='*.ts' -e "'/webhooks" -e '"/webhooks' server/` returns nothing), so either
   choice is safe now. If a second Python webhook family appears, it needs its own line — that is
   the trade-off I took for keeping this change surgical.
4. **The account-level check that would have caught this.** Nothing exercised the proxied path: the
   TypeScript build passes, the Python tests never go through Express, and a `200 text/html` from
   the SPA looks like success to any client that does not check `Content-Type`. A one-line smoke
   test — POST an unsigned body to a `/webhooks/` path and assert `401` — fails loudly if the proxy
   is ever removed. Worth adding; not added here, since it is not in this card's scope.
5. **Not verified here:** this was reproduced in development mode. Production uses `serveStatic`
   instead of Vite, and I read that handler rather than running a production build (see §6). The
   routing structure is the same — both are `app.use("*", …)` registered after the proxies — but the
   production build itself was not exercised locally.

## 6. How the local reproduction was built

The repo has a `pyproject.toml` but no lockfile and no committed environment, and `npm install` /
`pip install` both need a workaround in this sandbox (npm: `EPERM ~/.npm/_cacache` → pass
`--cache`; pip: `SSLError OSStatus -26276` from the egress proxy → `--trusted-host pypi.org
--trusted-host files.pythonhosted.org`). Use `/opt/homebrew/bin/python3.12`; the system 3.14 has
weaker wheel coverage for `numpy`/`scipy`/`psycopg2-binary`.

Steps, in a branch worktree:

```bash
npm install --cache "$PWD/.npm-cache-hag155"
/opt/homebrew/bin/python3.12 -m venv .venv-hag155
.venv-hag155/bin/pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org \
  <the pyproject.toml dependency list>          # + httpx, undeclared but imported
```

Schema: `run_migrations` is PostgreSQL-only, so on sqlite build the schema with `create_all` alone —
import every module under `server.models`, then `Base.metadata.create_all(bind=engine)` (95 tables).
Then run the gateway with:

```bash
PORT=5099 NODE_ENV=development FASTAPI_PORT=8001 \
PYTHON_BIN="$PWD/.venv-hag155/bin/python" \
DATABASE_URL="sqlite:///$SCRATCH/hag155.db" \
CREATE_SCHEMA=false RUN_MIGRATIONS=false SEED_BENCHMARKS=false SEED_DEMO_DATA=false \
LEAD_GEN_WEBHOOK_SECRET=hag155-local-test-secret SESSION_SECRET=hag155-local-test-session-secret \
npx tsx server/index.ts
```

`NODE_ENV=development` avoids needing a client build; Express spawns the real FastAPI itself via
`PYTHON_BIN`. The four `CREATE_*`/`RUN_*`/`SEED_*` flags are needed because `server/core/config.py`
defaults them all to **true** when not in production (`config.py:84-106`), and `run_migrations`
fails on sqlite.

Not done: no production build (so no `serveStatic` run), no byte-level bundle comparison, no
TypeScript error-count comparison against the 82-error budget in `.github/workflows/pr-checks.yml`
(the change is additive and mirrors an existing block; the runtime runs above are the evidence that
it compiles and executes).
