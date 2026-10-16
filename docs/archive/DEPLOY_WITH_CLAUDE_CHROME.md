# Deploy FounderConsole via Replit — Claude for Chrome Prompt

## Copy and paste this entire prompt into Claude for Chrome while on replit.com

---

```
I need you to help me deploy my FounderConsole application on Replit. Walk me through each step and execute the actions in my browser. Here's exactly what needs to happen:

## STEP 1: Open/Navigate to my Replit project

Navigate to https://replit.com and sign in if needed. Then find or open my existing project called "predixen-intelligence-os" (or "FounderConsole"). If it doesn't exist yet, I need to create a new Repl:
- Click "+ Create Repl"
- Choose "Import from GitHub"
- Paste my repo URL
- Name it "predixen-intelligence-os"
- Click "Import from GitHub"

## STEP 2: Verify Modules

Once the project is open, go to the "Modules" or "Tools" panel and make sure these modules are enabled:
- Node.js 20
- Python 3.11
- PostgreSQL 16
- Web (for port forwarding)

If any are missing, add them.

## STEP 3: Configure Secrets (Environment Variables)

Go to the "Secrets" tab (lock icon in the left sidebar). Add each of these secrets one by one. Click "+ New Secret" for each:

### REQUIRED SECRETS (app will not start without these):

1. Secret key: `SESSION_SECRET`
   Value: Generate a random string. Use this: `a]3kF9$mP2xL7vN8qR4wT6yB1cD5eG0hJ`
   (Or any 32+ character random string)

2. Secret key: `ADMIN_MASTER_EMAIL`
   Value: `vysheshk@gmail.com`

3. Secret key: `ADMIN_MASTER_PASSWORD`
   Value: (I'll type this myself - just create the secret field)

### LLM API KEYS (at least one required for AI features):

4. Secret key: `ANTHROPIC_API_KEY`
   Value: (I'll paste my key - just create the field)

5. Secret key: `OPENAI_API_KEY`
   Value: (I'll paste my key - just create the field)

6. Secret key: `GOOGLE_GEMINI_API_KEY`
   Value: (I'll paste my key - just create the field)

7. Secret key: `PERPLEXITY_API_KEY`
   Value: (I'll paste my key - just create the field)

### APP CONFIGURATION:

8. Secret key: `ENVIRONMENT`
   Value: `production`

9. Secret key: `APP_BASE_URL`
   Value: `https://predixen-intelligence-os.replit.app`
   (Update this later if I set up a custom domain)

10. Secret key: `CORS_ORIGINS`
    Value: `https://predixen-intelligence-os.replit.app,https://founderconsole.ai`

### FIRST-TIME DATABASE SETUP (set to "true" now, change to "false" after first successful run):

11. Secret key: `CREATE_SCHEMA`
    Value: `true`

12. Secret key: `RUN_MIGRATIONS`
    Value: `true`

13. Secret key: `SEED_BENCHMARKS`
    Value: `true`

14. Secret key: `SEED_DEMO_DATA`
    Value: `true`

### OPTIONAL INTEGRATION SECRETS (add if I have the keys):

15. Secret key: `STRIPE_SECRET_KEY`
    Value: (skip if not available)

16. Secret key: `RESEND_API_KEY`
    Value: (skip if not available)

17. Secret key: `TWILIO_ACCOUNT_SID`
    Value: (skip if not available)

18. Secret key: `TWILIO_AUTH_TOKEN`
    Value: (skip if not available)

19. Secret key: `TWILIO_PHONE_NUMBER`
    Value: (skip if not available)

## STEP 4: Verify the .replit File

Open the `.replit` file in the editor and make sure it contains this deployment config:

```toml
[deployment]
deploymentTarget = "autoscale"
run = ["node", "./dist/index.cjs"]
build = ["npm", "run", "build"]
```

If it's not there, add it.

## STEP 5: Install Dependencies

Open the Shell tab and run these commands one at a time, waiting for each to complete:

```bash
npm install
```

Then:
```bash
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary pydantic pydantic-settings python-jose passlib bcrypt pandas numpy scipy openpyxl pdfplumber pdf2image Pillow openai email-validator twilio resend httpx python-multipart cryptography slowapi
```

## STEP 6: Test in Development Mode

Click the green "Run" button (or run `npm run dev` in the shell). Wait for:
- "Server running on port 5000" in the console
- "FastAPI started on port 8001"
- The Webview should show the app loading

If you see errors, tell me what they say.

## STEP 7: Verify Health Endpoints

In the Webview URL bar, navigate to:
- `https://[repl-url]/health` — should return JSON with status
- `https://[repl-url]/api/health` — should return FastAPI health

## STEP 8: Deploy to Production

Once dev mode works:

1. Stop the dev server (Ctrl+C in shell)
2. Click the "Deploy" button in the top right
3. Select "Autoscale" deployment type
4. Build command should auto-fill: `npm run build`
5. Run command should auto-fill: `node ./dist/index.cjs`
6. Click "Deploy"
7. Wait for the build to complete (5-10 minutes)

## STEP 9: Post-Deployment Secrets Update

After the first deployment succeeds and the app is running, go back to Secrets and change:
- `CREATE_SCHEMA` → `false`
- `RUN_MIGRATIONS` → `false`
- `SEED_BENCHMARKS` → `false`
- `SEED_DEMO_DATA` → `false`

Then redeploy.

## STEP 10: Custom Domain (Optional)

If I want to point founderconsole.ai to this deployment:
1. Go to the deployment settings
2. Click "Custom Domain"
3. Enter: `founderconsole.ai`
4. Copy the CNAME record shown
5. I'll add the DNS record at my domain registrar

## TROUBLESHOOTING

If the build fails:
- Check shell output for specific error messages
- Common fix: run `npm run build` manually in shell first to see errors
- If Python imports fail: run pip install for the missing package

If the app starts but shows blank page:
- Check browser console for errors
- Verify CORS_ORIGINS includes the Replit URL

If database errors:
- Verify PostgreSQL module is enabled (it auto-provides DATABASE_URL)
- Try setting CREATE_SCHEMA=true and restarting

Please proceed step by step, pausing at each step to confirm with me before moving on. Start with Step 1.
```

---

## Architecture Reference (for your knowledge)

```
Port 5000 (Express/Node.js) → serves frontend + proxies API
Port 8001 (FastAPI/Python)   → backend API

Build: npm run build
  ├─ Vite compiles React → dist/public/
  └─ esbuild bundles Node server → dist/index.cjs

Run: node dist/index.cjs
  ├─ Opens port 5000 immediately
  ├─ Spawns: python -m uvicorn server.main:app --port 8001
  ├─ Proxies /api/* → FastAPI
  └─ Serves static files from dist/public/
```

## Required Files in Your Project
- `.replit` — already configured ✓
- `package.json` — scripts: dev, build, start ✓
- `server/index.ts` — Node entry point ✓
- `server/main.py` — FastAPI entry point ✓
- `pyproject.toml` — Python dependencies ✓
- `vite.config.ts` — Frontend build config ✓
