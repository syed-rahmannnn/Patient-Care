# Full-stack image for the Patient Care backend.
#
# Stage 1 builds the React admin dashboard (web/) and stage 2 copies the built
# assets into the Python image at /web/dist — which is exactly where the backend
# looks for them:  app/main.py -> Path(__file__).parents[2] / "web" / "dist"
# resolves to /web/dist when the app lives at /app/app/main.py. This gives the
# "single-service deploy" the code is written for: FastAPI serves /api, /ws AND
# the admin site from the same origin (so the web app's relative /api + /ws URLs
# and same-origin WebSockets just work behind Dokploy's Traefik / any HTTPS proxy).
#
# Build context is the repo ROOT (see docker-compose.yml), not ./backend.

# ---- Stage 1: build the admin dashboard ----
FROM node:20-bookworm-slim AS web
WORKDIR /web
# Cap V8 heap so the Vite/tsc build stays within the Pi's memory + swap budget.
ENV NODE_OPTIONS=--max-old-space-size=2048
COPY web/package.json web/package-lock.json ./
# `npm ci` is strict about lockfile sync; fall back to `npm install` if it drifts.
RUN npm ci || npm install
COPY web/ ./
RUN npm run build

# ---- Stage 2: backend runtime ----
FROM python:3.12-slim AS backend
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

# Built admin site — served by app/main.py's SPA fallback at /web/dist.
COPY --from=web /web/dist /web/dist

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
