# n8n → predixen: HMAC-signed webhook calls

Every call from n8n to predixen's `/webhooks/lead-gen/*` endpoints must be signed with HMAC-SHA256 using the shared secret in `LEAD_GEN_WEBHOOK_SECRET`. Without a valid `X-Predixen-Signature` header, the endpoint returns 401.

## Step 1 — store the secret in n8n

Generate a secret once (same value in both predixen and n8n):

```bash
openssl rand -hex 32
# example: 5a7d8e9f2c1b4a6e8d9f2c1b4a6e8d9f2c1b4a6e8d9f2c1b4a6e8d9f2c1b4a6e
```

In n8n: **Settings → Variables** (Cloud) or env vars (self-hosted) — add:

```
LEAD_GEN_WEBHOOK_SECRET = <that hex value>
PREDIXEN_HOST = https://your-predixen-host.com
```

In predixen's env: set the identical value for `LEAD_GEN_WEBHOOK_SECRET`.

## Step 2 — add a Function node before each HTTP node that calls predixen

Insert a **Code** node (JavaScript) named `Sign request` immediately before each predixen-bound HTTP node. Paste:

```javascript
// Code node: Sign request
// Input: { body: {...} }   — whatever payload you're about to POST
// Output: { body, signature } — pass both downstream to the HTTP node

const crypto = require('crypto');

const secret = $vars.LEAD_GEN_WEBHOOK_SECRET;
if (!secret) {
  throw new Error("LEAD_GEN_WEBHOOK_SECRET not set in n8n variables");
}

// The HTTP node MUST send EXACTLY this body string — we're signing the bytes.
// Canonical JSON (stable key order, no whitespace) avoids signature drift.
const payload = $json.body ?? $json;
const canonical = JSON.stringify(payload);
const signature = crypto
  .createHmac('sha256', secret)
  .update(canonical)
  .digest('hex');

return [{
  json: {
    body: payload,         // pass-through for the HTTP node
    bodyString: canonical, // HTTP node uses this as raw body
    signature,
  },
}];
```

## Step 3 — configure the HTTP node

For each HTTP node that posts to `/webhooks/lead-gen/*`:

- **Method:** POST
- **URL:** `={{ $vars.PREDIXEN_HOST }}/webhooks/lead-gen/ingest` (or `/event`, `/simulation`)
- **Authentication:** None
- **Send Body:** Yes → **Body Content Type:** Raw → **Body:** `={{ $json.bodyString }}`
- **Send Headers:** Yes → add:
  - `Content-Type: application/json`
  - `X-Predixen-Signature: ={{ $json.signature }}`

The raw-body approach is crucial — if n8n re-serializes the JSON at send time, the bytes won't match what you signed and the signature check fails. Using `bodyString` from the Code node guarantees byte-for-byte match.

## Step 4 — where to put these in each sub-workflow

| Sub-workflow | Insert signing + HTTP before | Payload shape |
|---|---|---|
| **Sales Nav scraper** | After `Save Company to Google Sheet` — additionally POST each lead to predixen | `{email, first_name, last_name, company, linkedin_url, source: "scraper"}` |
| **Lead enrichment** | After Perplexity/Prospeo success — POST to `/ingest` (upserts) | `{email, summary, hook, website, sector, stage, hunter_status}` |
| **Cold outbound drip** | After each `Gmail send` success — POST to `/event` | `{email, kind: "email_sent", email_subject, gmail_thread_id, campaign_id}` |
| | After each reply-detection `true` branch — POST to `/event` | `{email, kind: "reply_received", reply_category, gmail_thread_id}` |
| **Inbound AI agent** | After classifier runs — POST to `/event` with classified category | `{email, kind: "reply_classified", reply_category}` |
| **Activation drip** | After `Welcome Email` sends — POST to `/event` | `{email, kind: "email_sent", email_subject: "welcome..."}` |

## Step 5 — test the signing

From your Mac terminal, simulate what n8n does:

```bash
export LEAD_GEN_WEBHOOK_SECRET="paste-your-hex-secret"
export PREDIXEN_HOST="https://your-predixen-host.com"

BODY='{"email":"test@example.com","first_name":"Test","company":"TestCo","source":"manual"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$LEAD_GEN_WEBHOOK_SECRET" -hex | awk '{print $2}')

curl -i -X POST "$PREDIXEN_HOST/webhooks/lead-gen/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Predixen-Signature: $SIG" \
  --data "$BODY"
```

Expected: `201 Created` + `{"lead_id": N, "action": "created"}`.

If you get `401 Invalid signature`, the secret doesn't match. If you get `500 LEAD_GEN_WEBHOOK_SECRET not set`, predixen isn't seeing the env var.

## Common pitfalls

1. **Whitespace in body changes the signature.** Always sign the exact bytes you send. If you let n8n auto-stringify, the output may vary. That's why we use `bodyString` from the Code node.
2. **Unicode escaping.** `JSON.stringify(...)` on the n8n side and `json.dumps(...)` on the Python side handle Unicode differently by default. Python's `json.dumps(data, separators=(',', ':'), ensure_ascii=False)` matches Node's `JSON.stringify`. The FastAPI endpoint reads `request.body()` raw so it doesn't matter as long as the request body byte string is what you signed.
3. **Trailing newline.** `echo` adds `\n`; `printf '%s'` doesn't. Use `printf` in curl tests.
