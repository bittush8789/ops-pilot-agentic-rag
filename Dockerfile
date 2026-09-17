# ── OpsPilot Dockerfile ───────────────────────────────────────────
# Multi-stage build: slim production image with all dependencies

# ── Stage 1: Build dependencies ───────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: Production image ──────────────────────────────────────
FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 opspilot

# Copy installed packages from builder
COPY --from=builder /root/.local /home/opspilot/.local

# Copy application source
COPY --chown=opspilot:opspilot backend/ ./backend/
COPY --chown=opspilot:opspilot frontend/ ./frontend/
COPY --chown=opspilot:opspilot data/ ./data/

# Switch to non-root user
USER opspilot

# Ensure local packages are on PATH
ENV PATH=/home/opspilot/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
