# FounderConsole

AI-powered financial intelligence platform for startups. Provides investor-grade diligence, probabilistic simulation, and ranked decision recommendations.

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Start development server (Node + FastAPI)
npm run dev
```

The application will be available at `http://localhost:5000`.

### Production

```bash
# Install production dependencies
npm ci

# Build the application
npm run build

# Start production server
npm start
```

## Architecture

- **Frontend**: React + TypeScript + Vite (served by Express)
- **Backend Gateway**: Express (Node.js) - proxies `/api` to FastAPI
- **API Server**: FastAPI (Python) - handles all business logic
- **Database**: PostgreSQL

The Node server spawns uvicorn as a child process and manages its lifecycle with:
- Graceful shutdown on SIGINT/SIGTERM/SIGHUP
- Automatic restart with exponential backoff (max 5 attempts)
- Health monitoring via `/health` endpoint

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SESSION_SECRET` | Secret key for session management |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ENV` | `development` | Environment mode (`development` or `production`) |
| `PORT` | `5000` | Port for the main application |
| `FASTAPI_PORT` | `8001` | Port for the FastAPI server |
| `FASTAPI_URL` | `http://localhost:8001` | URL for FastAPI server (used by proxy) |

### CORS Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | (see below) | Comma-separated list of allowed origins |

**CORS Defaults:**
- **Development**: `http://localhost:5173,http://localhost:5000,http://localhost:3000,http://0.0.0.0:5000`
- **Production**: Empty (must be explicitly set)

**Security Note**: Do not use wildcard (`*`) origins with credentials enabled. Always specify exact origins in production.

Example:
```bash
CORS_ORIGINS="https://app.founderconsole.ai,https://staging.founderconsole.ai"
```

### Database Initialization Flags

These flags control startup behavior. Defaults are `true` in development and `false` in production.

| Variable | Default (dev) | Default (prod) | Description |
|----------|---------------|----------------|-------------|
| `CREATE_SCHEMA` | `true` | `false` | Run `Base.metadata.create_all` on startup |
| `RUN_MIGRATIONS` | `true` | `false` | Run database migrations on startup |
| `SEED_BENCHMARKS` | `true` | `false` | Seed industry benchmark data |
| `SEED_DEMO_DATA` | `true` | `false` | Seed demo company and user data |

To enable in production:
```bash
CREATE_SCHEMA=true RUN_MIGRATIONS=true npm start
```

## Health Endpoints

### Node Server Health

```bash
GET /health
```

Response:
```json
{
  "ok": true,
  "fastapi": "up",
  "fastapi_status": "up",
  "uptime_seconds": 120,
  "version": "1.0.0",
  "environment": "development"
}
```

### FastAPI Health

```bash
GET /api/health
```

Response:
```json
{
  "status": "healthy"
}
```

## Running Tests

### Python Tests

```bash
# Run pytest from repo root
pytest

# With verbose output
pytest -v
```

### TypeScript Type Check

```bash
npm run check
```

## Development Notes

### Database Migrations

Migrations are idempotent and tracked to prevent re-running. In development, they run automatically on startup.

For manual migration control:
```bash
# Skip migrations
RUN_MIGRATIONS=false npm run dev

# Skip all initialization
CREATE_SCHEMA=false RUN_MIGRATIONS=false SEED_BENCHMARKS=false SEED_DEMO_DATA=false npm run dev
```

### Graceful Shutdown

The Node server handles graceful shutdown:
1. Stops accepting new connections
2. Sends SIGTERM to uvicorn
3. Waits up to 5 seconds for graceful exit
4. Sends SIGKILL if necessary
5. Exits process

### FastAPI Supervision

If uvicorn crashes unexpectedly:
1. Logs the exit code
2. Waits with exponential backoff (1s, 2s, 4s, 8s, 16s)
3. Attempts restart (max 5 attempts)
4. Logs clearly if giving up

## Admin Access

Platform admin credentials are configured via environment:
- `ADMIN_MASTER_EMAIL`
- `ADMIN_MASTER_PASSWORD`
