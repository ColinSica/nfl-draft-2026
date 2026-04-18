# Multi-stage build: Node for the frontend bundle, Python slim for the API.
# Total final image ~300MB, fits on every free tier (Render, Fly.io, Railway).

# ---------- Stage 1: build the React frontend ----------
FROM node:20-slim AS frontend

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build   # emits to /app/src/api/static via vite.config alias


# ---------- Stage 2: Python runtime ----------
FROM python:3.11-slim

WORKDIR /app

# System deps for pandas/numpy wheels (most are prebuilt but keep a guard)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code + data
COPY src/ ./src/
COPY data/ ./data/
COPY run_dashboard.py ./

# Copy the prebuilt frontend from stage 1
COPY --from=frontend /app/src/api/static/ /app/src/api/static/

# Render/Fly/Railway all inject PORT. Default to 8000 for local Docker tests.
ENV PORT=8000
# Cap sim count on public hosts so one visitor can't monopolize the box.
# DRAFT_MAX_SIMS overrides the 5000 default in the POST /api/simulate handler.
ENV DRAFT_MAX_SIMS=200

EXPOSE 8000

# uvicorn directly — skips the frontend-build check in run_dashboard.py
# since the bundle was already baked into the image.
CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
