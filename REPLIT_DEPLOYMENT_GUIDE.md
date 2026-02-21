# FounderConsole Replit Deployment Guide

A comprehensive guide to deploying FounderConsole on Replit with all required configuration, secrets management, and troubleshooting steps.

## Prerequisites

### Replit Plan Requirements

- **Minimum Plan**: Replit Hacker plan (or higher)
- **Why**: FounderConsole requires:
  - Always-on server capability (not available on free tier)
  - PostgreSQL database module access
  - Custom domains support (for founderconsole.ai)
  - More CPU/memory resources for Python + Node.js dual runtime

### Required Modules

The `.replit` file already configures these modules automatically:
- `nodejs-20` - Node.js runtime for Express proxy and frontend
- `python-3.11` - Python runtime for FastAPI backend
- `postgresql-16` - Database persistence
- `web` - HTTP server module
- `python3` - Additional Python utilities

If deploying to a fresh Replit project, ensure these modules are enabled in the project settings.

### System Requirements

- Disk space: ~2GB (for node_modules + Python packages)
- RAM: Recommended 4GB+ for smooth development
- Build time: ~5-10 minutes for initial deployment

---

## Required Secrets (Environment Variables)

All secrets must be configured in Replit via **Secrets** (lock icon). **Do NOT commit secrets to version control.**

### Database Configuration
| Secret Name | Required | Example Value | Description |
|------------|----------|----------------|-------------|
| `DATABASE_URL` | ✅ Auto-provided | `postgresql://user:pass@localhost:5432/founderconsole` | PostgreSQL connection string. Replit provides this automatically when PostgreSQL module is added. |

### Session & Authentication
| Secret Name | Required | Example Value | Description |
|------------|----------|----------------|-------------|
| `SESSION_SECRET` | ✅ Yes | `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b` | 64-character hex string for session encryption. **MUST be set in production** or app will refuse to start. Generate: `openssl rand -hex 32` |
| `ADMIN_MASTER_EMAIL` | ✅ Yes | `admin@founderconsole.ai` | Primary admin email address. Must be a valid email. Used for initial admin account creation. |
| `ADMIN_MASTER_PASSWORD` | ✅ Yes | `SecurePassword123!` | Primary admin password. Minimum 8 characters recommended. Change after first login. |

### LLM & AI Providers
| Secret Name | Required | Example Value | Description |
|------------|----------|----------------|-------------|
| `AI_INTEGRATIONS_ANTHROPIC_API_KEY` | ❌ Optional | `sk-ant-v0-...` | Anthropic Claude API key for advanced reasoning tasks. Get from: https://console.anthropic.com/keys |
| `AI_INTEGRATIONS_OPENAI_API_KEY` | ❌ Optional | `sk-proj-...` | OpenAI API key for GPT models and vision tasks. Get from: https://platform.openai.com/api-keys |
| `AI_INTEGRATIONS_GEMINI_API_KEY` | ❌ Optional | `AIzaSy...` | Google Gemini API key. Get from: https://aistudio.google.com/apikey |
| `PERPLEXITY_API_KEY` | ❌ Optional | `pplx-...` | Perplexity API key for web search + LLM combo. Get from: https://www.perplexity.ai/api |

**Note**: At least one LLM provider should be configured for core AI features to work. OpenAI is recommended as fallback.

### Third-Party Integrations
| Secret Name | Required | Example Value | Description |
|------------|----------|----------------|-------------|
| `STRIPE_SECRET_KEY` | ❌ Optional | `sk_test_...` or `sk_live_...` | Stripe secret key for payment processing. Get from: https://dashboard.stripe.com/apikeys |
| `TWILIO_ACCOUNT_SID` | ❌ Optional | `AC1234567890abcdef...` | Twilio account SID for SMS features. Get from: https://www.twilio.com/console |
| `TWILIO_AUTH_TOKEN` | ❌ Optional | `your_auth_token_here` | Twilio auth token (paired with ACCOUNT_SID). Keep confidential. |
| `RESEND_API_KEY` | ❌ Optional | `re_...` | Resend email service API key for transactional emails. Get from: https://resend.com/api-keys |
| `RESEND_WEBHOOK_SECRET` | ❌ Optional | `whsec_...` | Resend webhook secret for email event tracking. |
| `NOTION_API_TOKEN` | ❌ Optional | `secret_...` | Notion API token for report export & integration. Get from: https://www.notion.so/my-integrations |
| `GITHUB_TOKEN` | ❌ Optional | `ghp_...` | GitHub personal access token for repo integrations. Get from: https://github.com/settings/tokens |

**Note**: Notion integration uses Replit Connectors for OAuth flow (preferred over manual token). See "Notion Integration Setup" section.

### Application Configuration
| Secret Name | Required | Example Value | Description |
|------------|----------|----------------|-------------|
| `APP_BASE_URL` | ⚠️ Conditional | `https://founderconsole.ai` | Public base URL of the app. Required for email links, OAuth redirects, and CORS. **Must be HTTPS in production.** |
| `CORS_ORIGINS` | ✅ Yes (Prod) | `https://founderconsole.ai,https://app.founderconsole.ai` | Comma-separated list of allowed origins. **Required in production** (no defaults). Development defaults to localhost origins. |
| `ENVIRONMENT` | ✅ Yes | `production` or `development` | Sets log level, error detail, and feature flags. Values: `development` or `production`. |

### Database Initialization Flags
**IMPORTANT**: These flags control one-time database initialization. Set to `true` for first deployment, then set to `false` for production.

| Secret Name | Required | First Deploy | Subsequent | Description |
|------------|----------|--------------|-----------|-------------|
| `CREATE_SCHEMA` | ✅ Yes | `true` | `false` | Whether to create database tables on startup. Set `true` only on first deployment, then `false` to prevent table drops on restart. |
| `RUN_MIGRATIONS` | ✅ Yes | `true` | `false` | Whether to run database migrations. Set `true` for first deployment and after code updates with schema changes, then `false`. |
| `SEED_BENCHMARKS` | ❌ Optional | `true` | `false` | Whether to populate benchmark comparison data (used for financial modeling context). Set `true` for demo/development, `false` for production. |
| `SEED_DEMO_DATA` | ❌ Optional | `true` | `false` | Whether to populate demo companies and scenarios. Set `true` for demo environments, `false` for production. |

**Default Behavior** (if not explicitly set):
- Development (`ENVIRONMENT=development`): All flags default to `true`
- Production (`ENVIRONMENT=production`): All flags default to `false`

### Optional Performance & Rate Limiting
| Secret Name | Required | Example Value | Description |
|------------|----------|----------------|-------------|
| `RATE_LIMIT_AUTH` | ❌ Optional | `5` | Authentication endpoint requests per minute. Default: 5 (prevents brute force). |
| `RATE_LIMIT_API` | ❌ Optional | `60` | General API requests per minute. Default: 60. |
| `RATE_LIMIT_UPLOAD` | ❌ Optional | `10` | File upload requests per minute. Default: 10. |

### Internal Secrets (Replit Auto-Provided)
These are automatically set by Replit and should **NOT** be manually configured:
| Secret Name | Description |
|------------|-------------|
| `PORT` | HTTP port (set to 5000 in `.replit`) |
| `REPL_IDENTITY` | Authentication token for Replit API access |
| `WEB_REPL_RENEWAL` | Web deployment identity token |
| `REPLIT_CONNECTORS_HOSTNAME` | Hostname for Replit Connectors (OAuth integrations) |

---

## Step-by-Step Deployment

### Step 1: Create/Import Project on Replit

#### Option A: Import from GitHub
1. Go to https://replit.com/new
2. Click "Import from GitHub"
3. Paste: `https://github.com/founderconsole/fund-flow`
4. Click "Import"
5. Wait for initial setup (~2-3 minutes)

#### Option B: Upload Files
1. Go to https://replit.com/new
2. Select "Node.js" template
3. Once created, upload files from this repository
4. Run `npm install && pip install -r requirements.txt`

### Step 2: Enable PostgreSQL Database

1. **Open Replit project**
2. Click the **Modules** icon (puzzle piece) in left sidebar
3. Search for **PostgreSQL**
4. Click **+ Create** to add PostgreSQL 16
5. Wait for database to initialize (~30 seconds)
6. **DATABASE_URL will be automatically added to Secrets**

**Verification**: In the Secrets tab, verify `DATABASE_URL` is present (looks like `postgresql://user:pass@localhost:5432/founderconsole_db`)

### Step 3: Configure All Required Secrets

1. **Click Secrets (lock icon)** in left sidebar
2. **Add all secrets from the table below:**

#### Minimal Production Secrets (Required)
```
SESSION_SECRET = <64-char hex string from: openssl rand -hex 32>
ADMIN_MASTER_EMAIL = your-email@example.com
ADMIN_MASTER_PASSWORD = YourSecurePassword123!
APP_BASE_URL = https://founderconsole.ai
CORS_ORIGINS = https://founderconsole.ai
ENVIRONMENT = production
```

#### First-Time Deployment Only (Set to true)
```
CREATE_SCHEMA = true
RUN_MIGRATIONS = true
SEED_BENCHMARKS = true
SEED_DEMO_DATA = true
```

#### Add at Least One LLM Provider
```
# Option 1: Anthropic (Recommended)
AI_INTEGRATIONS_ANTHROPIC_API_KEY = sk-ant-v0-...

# Option 2: OpenAI (Best for vision)
AI_INTEGRATIONS_OPENAI_API_KEY = sk-proj-...

# Option 3: Google Gemini
AI_INTEGRATIONS_GEMINI_API_KEY = AIzaSy...

# Optional: Perplexity (Web search + LLM)
PERPLEXITY_API_KEY = pplx-...
```

#### Optional: Email & Integrations
```
RESEND_API_KEY = re_...  # For transactional emails
STRIPE_SECRET_KEY = sk_test_...  # For payments (if needed)
```

### Step 4: First-Time Database Setup

**For the FIRST DEPLOYMENT ONLY:**

1. All initialization secrets already set from Step 3 (CREATE_SCHEMA=true, RUN_MIGRATIONS=true, SEED_BENCHMARKS=true, SEED_DEMO_DATA=true)
2. Click **Run** button (green play icon)
3. **Wait for startup sequence** (~30-60 seconds):
   - Node.js express server starts on port 5000
   - Python FastAPI backend starts on port 8001
   - Database migrations run automatically
   - Sample benchmarks and demo data populate (if SEED_* flags are true)
4. **Watch console for success message:**
   ```
   [startup] Port 5000 open and accepting connections
   [fastapi] Server is ready
   Deferred startup tasks completed successfully
   ```

### Step 5: Deploy to Production

#### Option A: Development/Testing (npm run dev)
```bash
# Already configured in .replit
npm run dev
```
- Runs with hot-reload
- Enables verbose logging
- No production optimizations

#### Option B: Production Deployment (npm run build + start)
1. **Set CREATE_SCHEMA, RUN_MIGRATIONS, SEED_BENCHMARKS, SEED_DEMO_DATA to `false`** in Secrets
2. Click **Deploy** button (rocket icon, top right)
3. Select **Autoscale** deployment
4. Wait for build (~5-10 minutes):
   - `npm run build` compiles TypeScript → JavaScript
   - Vite bundles frontend assets
   - All packages verified
5. Deployment completes and app goes live

**OR run in development mode:**
1. Keep flags as-is
2. Click **Run** button
3. Changes to code auto-reload

### Step 6: Post-Deployment Configuration

**AFTER successful first startup:**

1. **Update initialization secrets to `false` to prevent data loss:**
   ```
   CREATE_SCHEMA = false
   RUN_MIGRATIONS = false
   SEED_BENCHMARKS = false
   SEED_DEMO_DATA = false
   ```
2. **Restart the app** (click Run again or redeploy)
3. App now maintains schema and data across restarts

---

## First-Time vs Subsequent Deployments

### First-Time Deployment (Creating Database)

**Environment variables:**
```
CREATE_SCHEMA=true          # Create all tables
RUN_MIGRATIONS=true         # Run schema migrations
SEED_BENCHMARKS=true        # Populate benchmark data
SEED_DEMO_DATA=true         # Add sample companies
ENVIRONMENT=development     # Optional: start in dev mode
```

**What happens:**
- FastAPI creates database schema from SQLAlchemy models
- Alembic migrations apply any incremental changes
- Sample benchmarks (S&P 500, SaaS comparables) populate
- Demo company accounts create for testing
- Logs show: `Database tables created successfully`, `Benchmark data seeded`, `Demo data seeded`

**Expected console output:**
```
[startup] Port 5000 open and accepting connections
[fastapi] Creating database tables...
Database tables created successfully
[fastapi] Running migrations...
Migrations completed
[fastapi] Seeding benchmark data...
Benchmark data seeded
[fastapi] Seeding demo data...
Demo data seeded
[fastapi] Deferred startup tasks completed successfully
```

**Time**: ~60 seconds (database operations take longer first run)

### Subsequent Deployments (Database Exists)

**Environment variables:**
```
CREATE_SCHEMA=false         # Skip table creation (prevents data loss)
RUN_MIGRATIONS=false        # Skip unless code has schema changes
SEED_BENCHMARKS=false       # Don't re-seed (preserves user edits)
SEED_DEMO_DATA=false        # Don't re-seed
ENVIRONMENT=production      # Run in production mode
```

**What happens:**
- FastAPI skips schema creation (preserves existing data)
- No migrations run (unless RUN_MIGRATIONS explicitly set to true after code update)
- Benchmarks/demo data not re-seeded (preserves user data)
- App starts in ~5 seconds
- Logs show: `Skipping schema creation`, `Skipping migrations`, `Skipping benchmark seeding`, `Skipping demo data seeding`

**When to set RUN_MIGRATIONS=true:**
- After pulling code with database schema changes
- When deployment fails with schema errors
- When adding new tables/columns to models

**How to safely migrate:**
1. Set `RUN_MIGRATIONS=true` in Secrets
2. Click Run
3. Wait for migration to complete (logs show `Migrations completed`)
4. Set `RUN_MIGRATIONS=false` again
5. Click Run to restart

---

## Health Check Verification

### 1. Express Server Health Endpoint

```bash
curl https://your-replit-url.repl.co/health
```

Expected response:
```json
{
  "ok": true,
  "fastapi": "up",
  "fastapi_status": "up",
  "uptime_seconds": 1234,
  "version": "1.0.0",
  "environment": "production"
}
```

### 2. FastAPI Backend Health Endpoint

```bash
curl https://your-replit-url.repl.co/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "ready": true,
  "startup_error": null
}
```

**Field explanations:**
- `status: "healthy"` - FastAPI is running
- `ready: true` - Migrations and seeding completed
- `startup_error: null` - No initialization errors

### 3. Full Application Test

1. Open https://your-replit-url.repl.co in browser
2. Should see FounderConsole login page
3. Try logging in with demo credentials:
   - Email: admin@founderconsole.ai (from ADMIN_MASTER_EMAIL)
   - Password: Your ADMIN_MASTER_PASSWORD value
4. After login, should see dashboard

### 4. Check Console Logs

In Replit, click **Console** tab to see real-time logs:
- Express startup: `Port 5000 open and accepting connections`
- FastAPI startup: `Server is ready`
- Database: `Tables created`, `Migrations completed` (first run only)
- Any errors appear in red

### 5. WebSocket Connection Test

FounderConsole uses WebSockets for real-time updates. To verify:
1. Open browser DevTools (F12)
2. Go to **Network** → **WS** tab
3. Refresh page
4. Should see WebSocket connection to `wss://your-url/ws` with status 101
5. If missing, WebSocket proxy may need configuration

---

## Troubleshooting

### Issue: "FATAL: You must set SESSION_SECRET env var in production"

**Cause**: Session encryption key not configured for production environment.

**Fix**:
1. Generate a secure key: `openssl rand -hex 32`
2. Add to Secrets: `SESSION_SECRET = <generated_value>`
3. Restart app (click Run)

**Verification**: Log should show no error on startup.

---

### Issue: Database Connection Failed - "could not connect to server"

**Cause**: PostgreSQL module not enabled or DATABASE_URL not set.

**Fix**:
1. Click **Modules** (puzzle icon)
2. Search **PostgreSQL**
3. If not present, click **+ Create** to add
4. Wait 30 seconds for setup
5. Verify `DATABASE_URL` in Secrets (should look like `postgresql://...`)
6. Restart app

**Verification**: `curl` health endpoint and check for `database` in response.

---

### Issue: "FastAPI failed to start" or "Backend service unavailable"

**Cause**: Python dependencies missing, syntax error, or port conflict.

**Fix**:
1. Check console for error message (scroll up in Console tab)
2. If "ModuleNotFoundError", run: `pip install -r requirements.txt`
3. If port conflict: Kill existing process:
   ```bash
   fuser -k 8001/tcp 2>/dev/null || lsof -ti:8001 | xargs kill -9
   ```
4. Restart app

**Verification**: Check logs for `[fastapi] Server is ready` message.

---

### Issue: "Migrations failed" or "Schema error"

**Cause**: Database schema is out of sync with code models.

**Fix**:
1. Set `RUN_MIGRATIONS=true` in Secrets
2. Click Run
3. Wait for logs to show `Migrations completed`
4. Set `RUN_MIGRATIONS=false`
5. Restart

**If migration fails**:
1. Check error message in logs
2. May need to manually adjust migration files in `server/core/migrations/`
3. Or backup data and reset database (destructive):
   ```bash
   psql $DATABASE_URL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   ```
   Then set `CREATE_SCHEMA=true` and restart

---

### Issue: "AI/LLM features not working" or "OpenAI API key not configured"

**Cause**: No LLM API keys configured.

**Fix**: Add at least one of:
```
AI_INTEGRATIONS_ANTHROPIC_API_KEY = sk-ant-v0-...
AI_INTEGRATIONS_OPENAI_API_KEY = sk-proj-...
AI_INTEGRATIONS_GEMINI_API_KEY = AIzaSy...
PERPLEXITY_API_KEY = pplx-...
```

**Verification**: In app, try a feature that uses LLM (e.g., "AI Insights" button). Should generate output instead of error.

---

### Issue: CORS errors - "Cross-Origin Request Blocked"

**Cause**: Frontend URL not in `CORS_ORIGINS` environment variable.

**Example error in browser console:**
```
Access to XMLHttpRequest at 'https://replit.co/api/...' from origin
'https://my-domain.repl.co' has been blocked by CORS policy
```

**Fix**:
1. Add your domain to `CORS_ORIGINS` in Secrets:
   ```
   CORS_ORIGINS = https://founderconsole.ai,https://my-domain.repl.co
   ```
2. Restart app
3. Clear browser cache (Cmd+Shift+Delete on Mac, Ctrl+Shift+Delete on Windows)

**Verification**: Error should disappear and API calls work.

---

### Issue: "Email not sending" or "RESEND_API_KEY not configured"

**Cause**: Email service not configured or API key invalid.

**Fix**:
1. Get API key from https://resend.com/api-keys
2. Add to Secrets: `RESEND_API_KEY = re_...`
3. Optionally add: `RESEND_WEBHOOK_SECRET = whsec_...` for email tracking
4. Restart app

**Verification**: Try sending an email from app (e.g., invite user). Check logs for `Email sent successfully` message.

---

### Issue: "Notion integration not working"

**Cause**: Notion connector not connected via Replit UI, or API token invalid.

**Fix Option 1: Use Replit Connectors (Recommended)**
1. Click **Connectors** (plug icon) in sidebar
2. Search **Notion**
3. Click **Connect**
4. Authorize Notion OAuth flow
5. Connector will auto-populate access token

**Fix Option 2: Manual Token**
1. Create Notion integration at https://www.notion.so/my-integrations
2. Copy Secret Token
3. Add to Secrets: `NOTION_API_TOKEN = secret_...`
4. Restart app

**Verification**: Go to app and click "Export to Notion" feature. Should show your Notion pages.

---

### Issue: Deployment timeout or "Max restarts exceeded"

**Cause**: App taking too long to start (>2 minutes), FastAPI not becoming healthy.

**Fix**:
1. Check console for hang point (look for last log message)
2. If stuck on migrations: May need manual database reset
3. If stuck on seeding: Set SEED_BENCHMARKS=false, SEED_DEMO_DATA=false
4. Increase startup timeout (if available in Replit settings)
5. Kill background processes:
   ```bash
   pkill -f uvicorn
   pkill -f node
   sleep 2
   ```
6. Restart app

**Prevention**: In production, always keep SEED_* flags false to avoid startup delays.

---

### Issue: "Startup completed but ready: false" - Deferred tasks still running

**Cause**: Database migrations or seeding taking longer than expected, or stuck process.

**Expected behavior**: On first startup, this is normal. Task runs asynchronously while server accepts requests.

**If it's been >5 minutes**:
1. Check `/health` endpoint - may show `startup_error`
2. Look for errors in console logs
3. If specific seeding fails (e.g., benchmark data), try setting SEED_BENCHMARKS=false and restart
4. Check database size: might be corrupted data taking long to process

---

### Issue: Out of Memory (OOM) errors

**Cause**: Not enough RAM allocated on Replit plan, or memory leak in application.

**Fix**:
1. Upgrade Replit plan to Hacker (more RAM/CPU)
2. Check for memory leaks in logs
3. Reduce SEED_DEMO_DATA dataset size if too large
4. Kill background processes and restart

**Verification**: Run `free -h` in console to check available RAM.

---

## Custom Domain Setup

To make FounderConsole accessible at `founderconsole.ai`:

### Step 1: Get Replit Deployment URL

1. In your Replit project, click **Deploy** (rocket icon)
2. Copy the deployment URL (looks like `https://project-name.replit.dev`)
3. This is your target URL

### Step 2: Configure DNS

1. Go to your domain registrar (GoDaddy, Namecheap, Google Domains, etc.)
2. Navigate to DNS settings
3. Add a **CNAME record**:
   - **Name**: `founderconsole` (or `@` for root domain)
   - **Type**: CNAME
   - **Value**: `project-name.replit.dev`
   - **TTL**: 3600 (1 hour)

**Example (GoDaddy):**
```
Name: founderconsole
Type: CNAME
Value: fund-flow-project.replit.dev
TTL: 3600
```

**Save and wait** 15-30 minutes for DNS propagation.

### Step 3: Update CORS Configuration

1. In Replit Secrets, update:
   ```
   CORS_ORIGINS = https://founderconsole.ai,https://www.founderconsole.ai
   APP_BASE_URL = https://founderconsole.ai
   ```
2. Restart app

### Step 4: Enable HTTPS (Automatic)

Replit automatically provisions SSL certificates for custom domains via Let's Encrypt. **No additional steps needed.**

### Step 5: Verify

1. Open https://founderconsole.ai in browser
2. Should load FounderConsole app (may take 30 seconds first time)
3. Check certificate: Click lock icon → "Certificate is valid"
4. No CORS errors in browser console

**If not working:**
- Wait full DNS propagation (up to 2 hours)
- Clear DNS cache: `nslookup founderconsole.ai` (should resolve to Replit IP)
- Check CORS_ORIGINS again for typos
- Restart app after DNS propagation

### Optional: Redirect www to non-www

If you want `www.founderconsole.ai` to redirect to `founderconsole.ai`:

1. Add second CNAME for www subdomain:
   - **Name**: `www`
   - **Type**: CNAME
   - **Value**: `founderconsole.ai`

2. Update CORS: `CORS_ORIGINS = https://founderconsole.ai`

---

## Environment Reference

### Development Mode
```bash
ENVIRONMENT = development
CORS_ORIGINS = http://localhost:5000,http://localhost:5173,http://0.0.0.0:5000
CREATE_SCHEMA = true
RUN_MIGRATIONS = true
SEED_BENCHMARKS = true
SEED_DEMO_DATA = true
```

### Staging Mode
```bash
ENVIRONMENT = production
CORS_ORIGINS = https://staging.founderconsole.ai
CREATE_SCHEMA = false
RUN_MIGRATIONS = false
SEED_BENCHMARKS = false
SEED_DEMO_DATA = false
```

### Production Mode
```bash
ENVIRONMENT = production
CORS_ORIGINS = https://founderconsole.ai,https://www.founderconsole.ai
APP_BASE_URL = https://founderconsole.ai
CREATE_SCHEMA = false
RUN_MIGRATIONS = false
SEED_BENCHMARKS = false
SEED_DEMO_DATA = false
SESSION_SECRET = <64-char hex>
ADMIN_MASTER_EMAIL = ops@founderconsole.ai
ADMIN_MASTER_PASSWORD = <strong password>
AI_INTEGRATIONS_OPENAI_API_KEY = sk-proj-...
```

---

## Monitoring & Maintenance

### Daily Checks

```bash
# Check app health
curl https://founderconsole.ai/health

# Check FastAPI backend
curl https://founderconsole.ai/api/health

# Check logs in Replit Console tab
# Look for errors or warnings
```

### Weekly Tasks

1. Monitor Replit usage (CPU, memory, disk)
2. Check for any failed migrations or startup errors
3. Verify email deliverability (send test email)
4. Test login flow with admin account

### Monthly Tasks

1. Review and rotate SESSION_SECRET if compromised
2. Update API keys (Stripe, Twilio, OpenAI) if near rate limits
3. Back up database:
   ```bash
   pg_dump $DATABASE_URL > backup.sql
   ```
4. Review CORS_ORIGINS for unused/expired domains

---

## Support & Resources

- **FounderConsole Docs**: https://docs.founderconsole.ai
- **Replit Docs**: https://docs.replit.com
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **PostgreSQL Docs**: https://www.postgresql.org/docs

---

## Deployment Checklist

Before going live:

- [ ] Replit Hacker plan activated
- [ ] PostgreSQL module enabled & DATABASE_URL confirmed
- [ ] SESSION_SECRET generated & set
- [ ] ADMIN_MASTER_EMAIL & ADMIN_MASTER_PASSWORD configured
- [ ] At least one LLM API key added (OpenAI recommended)
- [ ] APP_BASE_URL set to custom domain
- [ ] CORS_ORIGINS configured for custom domain
- [ ] ENVIRONMENT = production
- [ ] Database initialization flags set (CREATE_SCHEMA=true on first run, then false)
- [ ] First startup successful (all deferred tasks completed)
- [ ] Health endpoint returns `"ready": true`
- [ ] Admin login works with configured credentials
- [ ] Custom domain DNS configured & propagated
- [ ] HTTPS certificate valid
- [ ] CORS errors resolved
- [ ] Email integration tested (if using)
- [ ] LLM features working (ask AI question, test insights)

---

**Last Updated**: February 2026
**Maintained By**: FounderConsole DevOps Team
