# ── Stage 1: Build React frontend ────────────────────────────────────────────
FROM node:18-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci --silent
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app/backend

# System deps needed by pandas / scikit-learn on slim image
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download NLTK data so first request isn't slow
RUN python -c "import nltk; nltk.download('stopwords',quiet=True); nltk.download('punkt',quiet=True); nltk.download('punkt_tab',quiet=True)"

# Copy backend source
COPY backend/ .

# Copy the built React app — main.py looks for ../frontend/dist
# → /app/backend/../frontend/dist → /app/frontend/dist  ✓
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Create persistent data directory (mount Railway volume here)
RUN mkdir -p /app/backend/data

# Railway injects $PORT dynamically; fall back to 8000 for local runs
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
