# syntax=docker/dockerfile:1
# FounderConsole — single app image (Express gateway + FastAPI backend + worker).
# Express (dist/index.cjs) spawns uvicorn and the simulation worker itself,
# so one container runs all three processes — same model as Replit.

########## Stage 1: build client (Vite) + server bundle (esbuild) ##########
FROM node:20-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV NODE_ENV=production
RUN npm run build

########## Stage 2: production-only node_modules ##########
FROM node:20-bookworm-slim AS node-deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

########## Stage 3: runtime ##########
FROM node:20-bookworm-slim AS runtime
WORKDIR /app

# python3 = 3.11 on Debian bookworm (matches Replit).
# poppler-utils is required by pdf2image/pdfplumber for document ingestion.
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv poppler-utils curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv for lockfile-exact Python installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Python dependencies (exact versions from uv.lock) into /app/.venv —
# Express's resolvePythonCommand() finds .venv/bin/python automatically.
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv venv /app/.venv --python /usr/bin/python3 \
    && uv sync --frozen --no-dev --no-install-project

# Node runtime deps + built app
COPY --from=node-deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./

# Source needed at runtime (FastAPI Python code, shared schema, migrations, seed data)
COPY server ./server
COPY shared ./shared
COPY migrations ./migrations
COPY data ./data
COPY scripts ./scripts

ENV NODE_ENV=production \
    ENVIRONMENT=production \
    PYTHON_BIN=/app/.venv/bin/python \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    FASTAPI_PORT=8001

EXPOSE 5000

# Generous start period: FastAPI deferred startup + first-boot schema creation take a while
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=5 \
  CMD curl -fsS http://localhost:5000/health || exit 1

CMD ["node", "dist/index.cjs"]
