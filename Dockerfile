# ── Stage 1: Build React frontend ────────────────────────────────────────────
FROM node:18-alpine AS frontend-build
WORKDIR /app
# Copy only package files first so npm install layer is cached
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci --silent
# Copy source and build
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app/backend

# System deps needed by pandas on slim image
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy the built React app from stage 1
# main.py resolves: os.path.dirname(__file__)/../frontend/dist
# → /app/backend/../frontend/dist → /app/frontend/dist  ✓
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

EXPOSE 7860
# HF Spaces injects $PORT=7860; fall back for local docker run
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
